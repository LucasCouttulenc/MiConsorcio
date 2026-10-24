import json
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import number_format
from django.utils.http import content_disposition_header
from django.views.decorators.http import require_POST

from usuarios.models import Propietario
from django.core.exceptions import ValidationError
from .forms import FormularioPago, FormularioServicioRecurrente, validar_comprobante
from consorcios.models import Consorcio, GrupoProrrateo, TipoReparto, UnidadFuncional
from .models import imputar_pago, Gasto, Liquidacion, TipoGasto, Pago, DetalleGastoUF, DetalleLiquidacionUF, NotificacionLiquidacion, ServicioRecurrente
from .pdf import generar_pdf_liquidacion, generar_recibo_pago_pdf
from .services import procesar_liquidacion_periodo, generar_resumen_uf_pdf
from consorcios.alicuotas import consorcio_tiene_alicuotas_validas, suma_alicuotas

MONTO_MAXIMO_GASTO = Decimal('10000000000')  # Gasto.monto: max_digits=12, decimal_places=2


class BorradorExistente(ValueError):
    def __init__(self, liquidacion):
        super().__init__('Ya existe un borrador para ese consorcio y período.')
        self.url = reverse('editar_liquidacion', args=[liquidacion.pk])


def consorcios_permitidos(usuario):
    if usuario.is_superuser:
        return Consorcio.objects.all()
    return Consorcio.objects.filter(administradores__usuario=usuario).distinct()


def liquidacion_permitida(request, liquidacion_id):
    return get_object_or_404(Liquidacion.objects.filter(
        consorcio__in=consorcios_permitidos(request.user)
    ).select_related('consorcio'), pk=liquidacion_id)


@login_required
@permission_required('consorcios.view_consorcio', raise_exception=True)
def listar_liquidaciones(request):
    consorcios = consorcios_permitidos(request.user).order_by('nombre')
    consorcio_id = request.GET.get('consorcio', '')
    liquidaciones = Liquidacion.objects.filter(consorcio__in=consorcios).select_related('consorcio')
    if consorcio_id:
        if not consorcio_id.isdecimal() or not consorcios.filter(pk=consorcio_id).exists():
            raise Http404('Consorcio no disponible')
        liquidaciones = liquidaciones.filter(consorcio_id=consorcio_id)
    return render(request, 'listar_liquidaciones.html', {
        'consorcios': consorcios, 'consorcio_id': str(consorcio_id),
        'borradores': liquidaciones.filter(cerrada=False).order_by('-actualizada'),
        'finalizadas': liquidaciones.filter(cerrada=True).order_by('-periodo', '-fecha_emision', '-pk'),
    })




@login_required
@permission_required('consorcios.view_consorcio', raise_exception=True)
def generar_liquidacion(request, liquidacion_id=None):
    from consorcios.models import Rubro  

    consorcios = consorcios_permitidos(request.user).order_by('nombre')

    # Inicializar los 3 diccionarios ANTES del for
    rubros_por_consorcio = {}
    columnas_por_rubro = {}
    personal_por_consorcio = {} 

    for c in consorcios:
        # 1. Garantizar rubro "REMUNERACIONES AL PERSONAL"
        rubro_sueldos, _ = Rubro.objects.get_or_create(
            consorcio=c,
            nombre='REMUNERACIONES AL PERSONAL',
        )

        # 2. Rubros y columnas
        rubros = c.rubros.all().order_by('nombre')
        rubros_por_consorcio[c.pk] = [
            {'val': r.pk, 'nombre': r.nombre} for r in rubros
        ]
        for r in rubros:
            columnas_por_rubro[r.pk] = [
                {
                    'val': col.pk,
                    'codigo': col.codigo,
                    'nombre': col.nombre,
                    'tipo_reparto': col.tipo_reparto,
                }
                for col in r.columnas.all().order_by('codigo')
            ]

        # 3. Personal con concepto y rubro armados
        personal_por_consorcio[c.pk] = {
            'rubro_id': rubro_sueldos.pk,
            'items': [
                {
                    'concepto': (
                        f"Sueldo: {p.nombre} {p.apellido}"
                        + (
                            f" - {p.empresa_tercerizada}"
                            if p.tipo_contratacion == 'tercerizado' and p.empresa_tercerizada
                            else ''
                        )
                    ),
                    'tipo': 'ordinario',
                }
                for p in c.personal.all().order_by('apellido', 'nombre')
            ],
        }

    # 4. Servicios recurrentes activos: el JS decide cuáles corresponden al período elegido
    servicios_por_consorcio = {}
    for s in ServicioRecurrente.objects.filter(consorcio__in=consorcios, activo=True).select_related('columna'):
        servicios_por_consorcio.setdefault(s.consorcio_id, []).append({
            'id': s.pk,
            'concepto': s.concepto,
            'tipo': s.tipo,
            'rubro_id': s.columna.rubro_id,
            'columna_id': s.columna_id,
            'monto': str(s.monto_sugerido) if s.monto_sugerido is not None else '',
            'frecuencia': s.frecuencia_meses,
            'inicio': s.periodo_inicio,
            'fin': s.periodo_fin,
        })

    liquidacion = liquidacion_permitida(request, liquidacion_id) if liquidacion_id else None
    if liquidacion and liquidacion.cerrada:
        return redirect('detalle_liquidacion', liquidacion_id=liquidacion.pk)

    consorcio_id = request.GET.get('consorcio', '')
    if consorcio_id and (not consorcio_id.isdecimal() or not consorcios.filter(pk=consorcio_id).exists()):
        raise Http404('Consorcio no disponible')

    return render(request, 'generar_liquidacion.html', {
        'consorcios': consorcios,
        'liquidacion': liquidacion,
        'datos_iniciales': liquidacion.datos_borrador if liquidacion else {},
        'consorcio_inicial': liquidacion.consorcio_id if liquidacion else consorcio_id,
        'rubros_por_consorcio': rubros_por_consorcio,
        'columnas_por_rubro': columnas_por_rubro,
        'personal_por_consorcio': personal_por_consorcio,
        'servicios_por_consorcio': servicios_por_consorcio,
    })

def leer_datos(request, finalizar=False):
    consorcio_id = request.POST.get('consorcio', '')
    mes, anio = request.POST.get('mes', ''), request.POST.get('anio', '')
    if not consorcio_id.isdecimal() or not mes.isdecimal() or not anio.isdecimal() or not 1 <= int(mes) <= 12 or not 2000 <= int(anio) <= 2100:
        raise ValueError('Seleccioná un consorcio y un período válidos.')
    consorcio = get_object_or_404(consorcios_permitidos(request.user), pk=consorcio_id)
    periodo = f'{int(anio):04d}-{int(mes):02d}'
    cierre, vencimiento = request.POST.get('fecha_cierre', ''), request.POST.get('fecha_vencimiento_1', '')
    try:
        fecha_cierre = date.fromisoformat(cierre) if cierre else None
        fecha_vencimiento = date.fromisoformat(vencimiento) if vencimiento else None
    except ValueError as exc:
        raise ValueError('Revisá las fechas ingresadas.') from exc
    if finalizar and (not fecha_cierre or not fecha_vencimiento):
        raise ValueError('Completá el cierre y el vencimiento antes de finalizar.')
    try:
        gastos = json.loads(request.POST.get('gastos', '[]'))
    except json.JSONDecodeError as exc:
        raise ValueError('Los gastos enviados no tienen un formato válido.') from exc
    if not isinstance(gastos, list) or len(gastos) > 300:
        raise ValueError('Los gastos enviados no tienen un formato válido.')
    filas = set()
    for gasto in gastos:
        if not isinstance(gasto, dict) or not isinstance(gasto.get('fila'), str) or not gasto['fila'] or len(gasto['fila']) > 50 or gasto['fila'] in filas:
            raise ValueError('Hay filas de gasto duplicadas o inválidas.')
        filas.add(gasto['fila'])
        if finalizar:
            try:
                monto = Decimal(str(gasto.get('monto', '')).replace(',', '.'))
            except InvalidOperation as exc:
                raise ValueError('Todos los gastos deben tener un monto válido.') from exc
            # NaN/Infinity se parsean bien pero rompen las comparaciones; el tope sale de max_digits=12 del modelo.
            if not monto.is_finite() or monto <= 0 or monto.as_tuple().exponent < -2:
                raise ValueError('Los montos deben ser positivos y tener hasta dos decimales.')
            if monto >= MONTO_MAXIMO_GASTO:
                raise ValueError('Hay un monto demasiado grande.')
            if not str(gasto.get('concepto', '')).strip() or gasto.get('tipo') not in TipoGasto.values or not gasto.get('grupo'):
                raise ValueError('Completá concepto, tipo y columna en cada gasto.')
    if finalizar and not gastos:
        raise ValueError('Agregá al menos un gasto antes de finalizar.')
    administracion = {campo: request.POST.get(campo, '').strip()[:200] for campo in (
        'admin_razon', 'admin_nombre', 'admin_domicilio', 'admin_fiscal',
        'admin_cuit', 'admin_rpa', 'admin_telefono', 'admin_mail')}
    return consorcio, periodo, fecha_cierre, fecha_vencimiento, {
        'consorcio': consorcio.pk, 'mes': f'{int(mes):02d}', 'anio': str(int(anio)),
        'fecha_cierre': cierre, 'fecha_vencimiento_1': vencimiento,
        'administracion': administracion, 'gastos': gastos,
    }


def guardar_borrador(request, finalizar=False):
    consorcio, periodo, cierre, vencimiento, datos = leer_datos(request, finalizar)
    
    if not consorcio_tiene_alicuotas_validas(consorcio):
        raise ValueError(
            f"El consorcio '{consorcio.nombre}' no tiene sus alícuotas sumando 100% "
            f"(suma actual: {suma_alicuotas(consorcio)}%). "
            "Corregí las alícuotas antes de liquidar."
        )
    
    
    
    liquidacion_id = request.POST.get('liquidacion_id', '')
    if liquidacion_id:
        liquidacion = liquidacion_permitida(request, liquidacion_id)
        if liquidacion.consorcio_id != consorcio.pk or liquidacion.periodo != periodo:
            existente = Liquidacion.objects.filter(consorcio=consorcio, periodo=periodo).first()
            if existente:
                if existente.cerrada:
                    raise ValueError('Ya existe una liquidación finalizada para ese período.')
                raise BorradorExistente(existente)
            liquidacion.consorcio = consorcio
            liquidacion.periodo = periodo
    else:
        liquidacion, creado = Liquidacion.objects.get_or_create(consorcio=consorcio, periodo=periodo)
        if not creado and not liquidacion.cerrada:
            raise BorradorExistente(liquidacion)
    if liquidacion.cerrada:
        raise ValueError('Esta liquidación ya fue finalizada y no puede modificarse.')
    liquidacion.fecha_cierre = cierre
    liquidacion.fecha_vencimiento_1 = vencimiento
    liquidacion.datos_borrador = datos
    liquidacion.save()
    return liquidacion


@login_required
@permission_required('consorcios.view_consorcio', raise_exception=True)
@require_POST
def autosave_liquidacion(request):
    try:
        with transaction.atomic():
            liquidacion = guardar_borrador(request)
    except BorradorExistente as exc:
        return JsonResponse({'error': str(exc), 'url': exc.url}, status=409)
    except (ValueError, Http404) as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    return JsonResponse({'id': liquidacion.pk, 'url': reverse('editar_liquidacion', args=[liquidacion.pk])})



@login_required
@permission_required('consorcios.view_consorcio', raise_exception=True)
@require_POST
def eliminar_borrador(request, liquidacion_id):
    liquidacion = get_object_or_404(Liquidacion, pk=liquidacion_id)
    
    # Verificamos que el usuario sea administrador del consorcio
    if liquidacion.consorcio not in consorcios_permitidos(request.user):
        messages.error(request, "No tenés permisos para eliminar este borrador.")
        return redirect('listar_liquidaciones')
        
    # Nos aseguramos de que no esté cerrada (solo borramos borradores)
    if liquidacion.cerrada:
        messages.error(request, "No podés eliminar una liquidación ya finalizada.")
        return redirect('listar_liquidaciones')
        
    liquidacion.delete()
    messages.success(request, f"Borrador del período {liquidacion.periodo} eliminado correctamente.")
    return redirect('listar_liquidaciones')


@login_required
@permission_required('consorcios.view_consorcio', raise_exception=True)
@require_POST
def finalizar_liquidacion(request):
    try:
        with transaction.atomic():
            liquidacion = guardar_borrador(request, finalizar=True)
            datos = liquidacion.datos_borrador
            liquidacion.gastos_cargados.all().delete()
            columnas = {str(g.pk): g for g in GrupoProrrateo.objects.filter(consorcio=liquidacion.consorcio)}
            servicios = {str(s.pk): s for s in ServicioRecurrente.objects.filter(consorcio=liquidacion.consorcio)}
            for posicion, gasto in enumerate(datos['gastos']):
                columna = columnas.get(str(gasto.get('grupo', '')))
                if not columna:
                    raise ValueError('Un gasto usa una columna que no pertenece al consorcio.')
                Gasto.objects.create(
                    liquidacion=liquidacion, consorcio=liquidacion.consorcio,
                    periodo=liquidacion.periodo, fecha_comprobante=date.today(),
                    posicion=posicion, concepto=str(gasto['concepto']).strip()[:200],
                    tipo=gasto['tipo'],
                    grupo=columna, monto=Decimal(str(gasto['monto']).replace(',', '.')),
                    servicio=servicios.get(str(gasto.get('servicio') or '')))
            procesar_liquidacion_periodo(liquidacion)
            liquidacion.documento = generar_pdf_liquidacion(liquidacion)
            liquidacion.cerrada = True
            liquidacion.save(update_fields=['documento', 'cerrada', 'actualizada'])
            NotificacionLiquidacion.objects.bulk_create([
                NotificacionLiquidacion(
                    propietario=detalle.unidad_funcional.propietario,
                    detalle_liquidacion=detalle,
                )
                for detalle in liquidacion.detalles_uf.select_related('unidad_funcional__propietario')
            ], ignore_conflicts=True)
    except BorradorExistente as exc:
        messages.info(request, str(exc))
        return redirect(exc.url)
    except (ValueError, Http404) as exc:
        messages.error(request, str(exc))
        borrador_id = request.POST.get('liquidacion_id', '')
        if borrador_id.isdecimal():
            return redirect('editar_liquidacion', liquidacion_id=borrador_id)
        return redirect('generar_liquidacion')
    messages.success(request, f'Liquidación {liquidacion.periodo} finalizada.')
    return redirect('detalle_liquidacion', liquidacion_id=liquidacion.pk)


@login_required
@permission_required('consorcios.view_consorcio', raise_exception=True)
def detalle_liquidacion(request, liquidacion_id):
    liquidacion = liquidacion_permitida(request, liquidacion_id)
    if not liquidacion.cerrada:
        return redirect('editar_liquidacion', liquidacion_id=liquidacion.pk)
    return render(request, 'detalle_liquidacion.html', {
        'liquidacion': liquidacion,
        'detalles': liquidacion.detalles_uf.select_related('unidad_funcional__propietario__usuario'),
        'gastos': liquidacion.gastos_cargados.select_related('grupo').order_by('posicion'),
    })


@login_required
@permission_required('consorcios.view_consorcio', raise_exception=True)
def descargar_documento(request, liquidacion_id):
    liquidacion = liquidacion_permitida(request, liquidacion_id)
    if not liquidacion.cerrada or not liquidacion.documento:
        raise Http404('Documento no disponible')
    respuesta = HttpResponse(bytes(liquidacion.documento), content_type='application/pdf')
    respuesta['Content-Disposition'] = content_disposition_header(True, f'liquidacion-{liquidacion.consorcio_id}-{liquidacion.periodo}.pdf')
    return respuesta


@login_required
@permission_required('consorcios.view_consorcio', raise_exception=True)
@require_POST
def subir_comprobante(request, gasto_id):
    gasto = get_object_or_404(Gasto.objects.select_related('liquidacion'), pk=gasto_id)
    liquidacion_permitida(request, gasto.liquidacion_id)
    archivo = request.FILES.get('comprobante')
    if not archivo:
        messages.error(request, 'No se selecciono ningun archivo.')
        return redirect('detalle_liquidacion', liquidacion_id=gasto.liquidacion_id)
    try:
        validar_comprobante(archivo)
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
        return redirect('detalle_liquidacion', liquidacion_id=gasto.liquidacion_id)
    gasto.comprobante = archivo
    gasto.save(update_fields=['comprobante'])
    messages.success(request, 'Comprobante adjuntado.')
    return redirect('detalle_liquidacion', liquidacion_id=gasto.liquidacion_id)


@login_required
@permission_required('consorcios.view_consorcio', raise_exception=True)
@require_POST
def alternar_visibilidad_comprobante(request, gasto_id):
    """Decide si el propietario puede ver la factura de un gasto imputado a su UF."""
    gasto = get_object_or_404(Gasto.objects.select_related('liquidacion'), pk=gasto_id)
    liquidacion_permitida(request, gasto.liquidacion_id)
    gasto.comprobante_visible = not gasto.comprobante_visible
    gasto.save(update_fields=['comprobante_visible'])
    return redirect('detalle_liquidacion', liquidacion_id=gasto.liquidacion_id)


@login_required
@permission_required('consorcios.view_consorcio', raise_exception=True)
@require_POST
def quitar_comprobante(request, gasto_id):
    gasto = get_object_or_404(Gasto.objects.select_related('liquidacion'), pk=gasto_id)
    liquidacion_permitida(request, gasto.liquidacion_id)
    if gasto.comprobante:
        gasto.comprobante.delete(save=False)
        gasto.comprobante = None
        gasto.save(update_fields=['comprobante'])
        messages.success(request, 'Comprobante quitado.')
    return redirect('detalle_liquidacion', liquidacion_id=gasto.liquidacion_id)


NOMBRES_MESES = ('', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre')


def periodo_legible(periodo):
    """'2026-09' -> 'Septiembre 2026'."""
    try:
        anio, mes = periodo.split('-')
        return f'{NOMBRES_MESES[int(mes)]} {anio}'
    except (ValueError, IndexError):
        return periodo


def dias_hasta(fecha, hoy):
    dias = (fecha - hoy).days
    if dias == 0:
        return 'Hoy'
    if dias == 1:
        return 'Mañana'
    if dias > 1:
        return f'En {dias} días'
    return f'Vencido hace {-dias} día{"s" if dias < -1 else ""}'


CLAVE_UNIDAD_PROPIETARIO = 'unidad_propietario'


def unidad_recordada(request, propietario):
    """La última UF que eligió el propietario, para mantenerla al pasar entre Inicio y Mis Expensas."""
    pk = request.session.get(CLAVE_UNIDAD_PROPIETARIO)
    if not pk:
        return None
    return UnidadFuncional.objects.filter(pk=pk, propietario=propietario).select_related('consorcio').first()


@login_required
def inicio_propietario(request):
    """Inicio del propietario: estado de cuenta de una UF, novedades y próximos vencimientos."""
    propietario = get_object_or_404(Propietario, usuario=request.user)
    unidades = UnidadFuncional.objects.filter(propietario=propietario).select_related('consorcio').order_by(
        'consorcio__nombre', 'piso', 'departamento'
    )
    unidad = unidades.filter(pk=request.GET.get('unidad')).first() if request.GET.get('unidad', '').isdecimal() else None
    unidad = unidad or unidad_recordada(request, propietario) or unidades.first()
    if not unidad:
        return render(request, 'inicio_propietario.html', {'sin_unidades': True})
    request.session[CLAVE_UNIDAD_PROPIETARIO] = unidad.pk

    hoy = date.today()
    detalles = list(DetalleLiquidacionUF.objects.filter(
        unidad_funcional=unidad, liquidacion__cerrada=True,
    ).select_related('liquidacion__consorcio').prefetch_related('imputaciones__pago').order_by('liquidacion__periodo'))
    impagos = [detalle for detalle in detalles if not detalle.esta_pagado]
    ultima = detalles[-1] if detalles else None
    capital = sum((detalle.deuda_total_actualizada for detalle in impagos), Decimal('0'))
    intereses = sum((detalle.interes(hoy) for detalle in impagos), Decimal('0'))
    pagos = list(Pago.objects.filter(detalle_liquidacion__unidad_funcional=unidad).select_related(
        'detalle_liquidacion__liquidacion'
    ).order_by('-fecha_registro'))
    pagos_en_revision = [pago for pago in pagos if pago.estado == 'pendiente']
    # Se informa el pago del período impago más viejo, salvo que ya tenga un comprobante en revisión.
    a_pagar = next((detalle for detalle in impagos if not detalle.tiene_pago_pendiente), None)

    vencimientos = [
        {
            'fecha': detalle.liquidacion.fecha_vencimiento_1,
            'titulo': f'Vencimiento: expensas {periodo_legible(detalle.liquidacion.periodo)}',
            'cuando': dias_hasta(detalle.liquidacion.fecha_vencimiento_1, hoy),
            'vencido': detalle.liquidacion.fecha_vencimiento_1 < hoy,
        }
        for detalle in impagos if detalle.liquidacion.fecha_vencimiento_1
    ]

    textos_pago = {
        'pendiente': ('Pago en revisión', 'La administración todavía tiene que validar tu comprobante'),
        'validado': ('Pago validado', 'La administración acreditó tu pago'),
        'rechazado': ('Pago rechazado', 'Revisá el motivo en el historial de pagos'),
    }
    novedades = [
        {
            'fecha': detalle.liquidacion.fecha_cierre or detalle.liquidacion.fecha_emision,
            'tipo': 'liquidacion',
            'titulo': f'Nueva liquidación: {periodo_legible(detalle.liquidacion.periodo)}',
            'texto': f'Te corresponde $ {number_format(detalle.monto_total, 2, force_grouping=True)}',
        }
        for detalle in detalles
    ] + [
        {
            'fecha': timezone.localdate(pago.fecha_registro),
            'tipo': pago.estado,
            'titulo': textos_pago[pago.estado][0],
            'texto': f'{textos_pago[pago.estado][1]} de $ {number_format(pago.monto_pagado, 2, force_grouping=True)} '
                     f'({periodo_legible(pago.detalle_liquidacion.liquidacion.periodo)}).',
        }
        for pago in pagos if pago.estado in textos_pago
    ]
    novedades.sort(key=lambda novedad: novedad['fecha'], reverse=True)

    return render(request, 'inicio_propietario.html', {
        'unidades': unidades,
        'unidad': unidad,
        'ultima': ultima,
        'ultima_label': periodo_legible(ultima.liquidacion.periodo) if ultima else '',
        'capital': capital,
        'intereses': intereses,
        'saldo': capital + intereses,
        'periodos_impagos': len(impagos),
        'proximo_vencimiento': min((v['fecha'] for v in vencimientos), default=None),
        'pagos_en_revision': len(pagos_en_revision),
        'a_pagar': a_pagar,
        'periodo_destino': (impagos[0] if impagos else ultima).liquidacion.periodo if ultima else None,
        'vencimientos': sorted(vencimientos, key=lambda v: v['fecha']),
        'novedades': novedades[:5],
        'hoy': hoy,
    })


@login_required
def mis_expensas(request):
    """Panel mensual del propietario para una de sus unidades funcionales."""
    propietario = get_object_or_404(Propietario, usuario=request.user)

    consorcios = Consorcio.objects.filter(
        unidades_funcionales__propietario=propietario
    ).distinct().order_by('nombre')
    consorcio = consorcios.filter(pk=request.GET.get('consorcio')).first() if request.GET.get('consorcio', '').isdecimal() else None
    recordada = unidad_recordada(request, propietario)
    consorcio = consorcio or (recordada.consorcio if recordada else None) or consorcios.first()
    if not consorcio:
        return render(request, 'mis_expensas.html', {
            'sin_unidades': True,
        })

    unidades = UnidadFuncional.objects.filter(propietario=propietario, consorcio=consorcio).order_by('piso', 'departamento')
    unidad = unidades.filter(pk=request.GET.get('unidad')).first() if request.GET.get('unidad', '').isdecimal() else None
    unidad = unidad or (recordada if recordada and recordada.consorcio_id == consorcio.pk else None) or unidades.first()
    if unidad:
        request.session[CLAVE_UNIDAD_PROPIETARIO] = unidad.pk
    periodos = list(Liquidacion.objects.filter(
        consorcio=consorcio, cerrada=True,
        detalles_uf__unidad_funcional__in=unidades,
    ).values_list('periodo', flat=True).distinct().order_by('-periodo'))
    periodo_actual = date.today().strftime('%Y-%m')
    periodo = request.GET.get('periodo', '')
    if periodo not in periodos:
        periodo = periodo_actual if periodo_actual in periodos else (periodos[0] if periodos else periodo_actual)

    detalle = None
    gastos = []
    resumen_rubros = []
    if unidad and periodo in periodos:
        detalle = DetalleLiquidacionUF.objects.select_related(
            'liquidacion', 'unidad_funcional', 'liquidacion__consorcio'
        ).prefetch_related('imputaciones__pago').filter(unidad_funcional=unidad, liquidacion__periodo=periodo, liquidacion__cerrada=True).first()
        if detalle:
            distribuciones = {
                distribucion.gasto_id: distribucion
                for distribucion in DetalleGastoUF.objects.filter(
                    unidad_funcional=unidad, gasto__liquidacion=detalle.liquidacion
                )
            }
            gastos_liquidacion = detalle.liquidacion.gastos_cargados.select_related(
                'grupo__rubro'
            ).prefetch_related('grupo__unidades').order_by('posicion', 'pk')
            por_rubro = {}
            for gasto in gastos_liquidacion:
                distribucion = distribuciones.get(gasto.pk)
                monto_asignado = distribucion.monto_asignado if distribucion else Decimal('0')
                rubro = gasto.rubro.nombre if gasto.rubro else 'Otros gastos'
                # Gasto imputado a mi UF: columna "particular" que solo pagan las UF elegidas, entre ellas la mía.
                unidades_que_pagan = list(gasto.grupo.unidades.all()) if gasto.grupo else []
                particular = bool(
                    gasto.grupo and gasto.grupo.tipo_reparto == TipoReparto.PARTICULAR and unidad in unidades_que_pagan
                )
                gastos.append({
                    'gasto': gasto, 'distribucion': distribucion, 'monto_asignado': monto_asignado, 'rubro': rubro,
                    'particular': particular, 'compartido_con': len(unidades_que_pagan) - 1 if particular else 0,
                })
                item = por_rubro.setdefault(rubro, {'nombre': rubro, 'total_edificio': Decimal('0'), 'tu_parte': Decimal('0')})
                item['total_edificio'] += gasto.monto
                item['tu_parte'] += monto_asignado
            resumen_rubros = list(por_rubro.values())

    indice = periodos.index(periodo) if periodo in periodos else -1
    anterior = periodos[indice + 1] if indice >= 0 and indice + 1 < len(periodos) else None
    siguiente = periodos[indice - 1] if indice > 0 else None
    pagos_pendientes = detalle.pagos.filter(estado='pendiente').exists() if detalle else False
    interes = detalle.interes() if detalle else Decimal('0')
    # Lo que cada pago validado canceló de este período, agrupado por pago.
    pagos_del_periodo = {}
    for imputacion in (detalle.imputaciones.all() if detalle else []):
        item = pagos_del_periodo.setdefault(imputacion.pago_id, {
            'fecha': imputacion.pago.fecha_pago, 'monto_pagado': imputacion.pago.monto_pagado, 'total': Decimal('0'),
            'interes': Decimal('0'), 'capital': Decimal('0'),
        })
        item[imputacion.concepto] += imputacion.monto
        item['total'] += imputacion.monto
    pagos_del_periodo = sorted(pagos_del_periodo.values(), key=lambda item: item['fecha'])
    # Períodos anteriores que siguen impagos: se arrastran como saldo anterior, con sus intereses.
    saldo_anterior = []
    if detalle:
        for previo in DetalleLiquidacionUF.objects.filter(
            unidad_funcional=unidad, liquidacion__cerrada=True, liquidacion__periodo__lt=detalle.liquidacion.periodo,
        ).select_related('liquidacion__consorcio').prefetch_related('imputaciones__pago').order_by('liquidacion__periodo'):
            if not previo.esta_pagado:
                saldo_anterior.append({
                    'periodo': periodo_legible(previo.liquidacion.periodo),
                    'capital': previo.deuda_total_actualizada,
                    'interes': previo.interes(),
                    'meses': previo.meses_de_atraso(),
                })
    total_saldo_anterior = sum((item['capital'] + item['interes'] for item in saldo_anterior), Decimal('0'))
    periodo_label = periodo_legible(periodo)
    return render(request, 'mis_expensas.html', {
        'consorcios': consorcios, 'consorcio': consorcio, 'unidades': unidades, 'unidad': unidad,
        'periodo': periodo, 'periodo_label': periodo_label, 'periodos': periodos, 'anterior': anterior, 'siguiente': siguiente,
        'detalle': detalle, 'gastos': gastos, 'resumen_rubros': resumen_rubros,
        'gastos_particulares': [item for item in gastos if item['particular']],
        'pagos_pendientes': pagos_pendientes,
        'interes': interes,
        'tasa_interes': consorcio.tasa_interes_mensual,
        'meses_atraso': detalle.meses_de_atraso() if detalle else 0,
        'interes_devengado': detalle.interes_devengado() if detalle else Decimal('0'),
        'pagos_del_periodo': pagos_del_periodo,
        'saldo_anterior': saldo_anterior,
        'total_saldo_anterior': total_saldo_anterior,
        'total_a_pagar': (total_saldo_anterior + detalle.deuda_total_actualizada + interes) if detalle else Decimal('0'),
    })


@login_required
def historial_pagos(request):
    """Historial de pagos y comprobantes informados por el propietario."""
    propietario = get_object_or_404(Propietario, usuario=request.user)
    pagos = Pago.objects.filter(
        detalle_liquidacion__unidad_funcional__propietario=propietario
    ).select_related(
        'detalle_liquidacion__liquidacion__consorcio', 'detalle_liquidacion__unidad_funcional'
    ).prefetch_related('imputaciones__detalle_liquidacion__liquidacion').order_by('-fecha_pago', '-fecha_registro')
    return render(request, 'historial_pagos.html', {
        'pagos': pagos,
    })


@login_required
def descargar_documento_propietario(request, liquidacion_id):
    propietario = get_object_or_404(Propietario, usuario=request.user)
    liquidacion = get_object_or_404(
        Liquidacion.objects.filter(
            cerrada=True, documento__isnull=False,
            detalles_uf__unidad_funcional__propietario=propietario,
        ).distinct(), pk=liquidacion_id,
    )
    respuesta = HttpResponse(bytes(liquidacion.documento), content_type='application/pdf')
    respuesta['Content-Disposition'] = content_disposition_header(
        True, f'liquidacion-{liquidacion.consorcio_id}-{liquidacion.periodo}.pdf'
    )
    return respuesta


@login_required
def descargar_recibo_pago(request, pago_id):
    """Recibo en PDF de un pago validado: para su propietario o para quien administra el consorcio."""
    pagos = Pago.objects.filter(estado='validado').select_related(
        'detalle_liquidacion__liquidacion__consorcio', 'detalle_liquidacion__unidad_funcional__propietario__usuario'
    )
    propietario = Propietario.objects.filter(usuario=request.user).first()
    permitido = Q(detalle_liquidacion__liquidacion__consorcio__in=consorcios_permitidos(request.user))
    if propietario:
        permitido |= Q(detalle_liquidacion__unidad_funcional__propietario=propietario)
    pago = get_object_or_404(pagos.filter(permitido), pk=pago_id)
    respuesta = HttpResponse(generar_recibo_pago_pdf(pago), content_type='application/pdf')
    respuesta['Content-Disposition'] = content_disposition_header(True, f'recibo-pago-{pago.pk:08d}.pdf')
    return respuesta


@login_required
def abrir_notificacion_liquidacion(request, notificacion_id):
    propietario = get_object_or_404(Propietario, usuario=request.user)
    notificacion = get_object_or_404(
        NotificacionLiquidacion.objects.select_related(
            'detalle_liquidacion__liquidacion', 'detalle_liquidacion__unidad_funcional'
        ),
        pk=notificacion_id,
        propietario=propietario,
    )
    if notificacion.leida_en is None:
        notificacion.leida_en = timezone.now()
        notificacion.save(update_fields=['leida_en'])

    detalle = notificacion.detalle_liquidacion
    destino = reverse('mis_expensas')
    parametros = (
        f'?consorcio={detalle.liquidacion.consorcio_id}'
        f'&unidad={detalle.unidad_funcional_id}'
        f'&periodo={detalle.liquidacion.periodo}'
    )
    return redirect(destino + parametros)

@login_required
def registrar_pago(request, detalle_id):
    """Procesa el formulario cuando el propietario sube un comprobante."""
    propietario = Propietario.objects.filter(usuario=request.user).first()
    detalles = DetalleLiquidacionUF.objects.select_related('liquidacion', 'unidad_funcional', 'liquidacion__consorcio')
    if propietario:
        detalles = detalles.filter(unidad_funcional__propietario=propietario)
    else:
        detalles = detalles.filter(liquidacion__consorcio__in=consorcios_permitidos(request.user))
    detalle = get_object_or_404(detalles, pk=detalle_id, liquidacion__cerrada=True)
    if detalle.esta_pagado or detalle.tiene_pago_pendiente:
        messages.info(request, 'Esta expensa ya está pagada o tiene un comprobante pendiente de revisión.')
        return redirect('mis_expensas')
    
    if request.method == 'POST':
        form = FormularioPago(request.POST, request.FILES)
        if form.is_valid():
            pago = form.save(commit=False)
            pago.detalle_liquidacion = detalle
            pago.estado = 'pendiente'
            pago.save()
            
            messages.success(request, 'Comprobante enviado exitosamente. Queda pendiente de validación.')
            
            # Verificamos si es Propietario para llevarlo a su panel
            if Propietario.objects.filter(usuario=request.user).exists():
                return redirect('mis_expensas')
            return redirect('detalle_liquidacion', liquidacion_id=detalle.liquidacion.id)
    else:
        monto_sugerido = detalle.deuda_total_actualizada + detalle.interes()
        form = FormularioPago(initial={'monto_pagado': monto_sugerido, 'fecha_pago': date.today()})
        
    return render(request, 'registrar_pago.html', {
        'form': form,
        'detalle': detalle
    })

@login_required
@permission_required('consorcios.view_consorcio', raise_exception=True)
def listar_pagos_pendientes(request):
    """Muestra al administrador los pagos que esperan revisión."""
    consorcios = consorcios_permitidos(request.user)
    pagos = Pago.objects.filter(
        detalle_liquidacion__liquidacion__consorcio__in=consorcios,
        estado='pendiente'
    ).order_by('-fecha_registro')
    
    return render(request, 'pagos_pendientes.html', {'pagos': pagos})

@login_required
@permission_required('consorcios.view_consorcio', raise_exception=True)
@require_POST
def procesar_pago(request, pago_id):
    """Aprueba o rechaza un pago."""
    pago = get_object_or_404(Pago, pk=pago_id)
    
    if pago.detalle_liquidacion.liquidacion.consorcio not in consorcios_permitidos(request.user):
        raise Http404('No tenés permisos para gestionar este pago.')
        
    estados = {'validar': 'validado', 'rechazar': 'rechazado'}
    accion = request.POST.get('accion')
    if accion not in estados:
        messages.error(request, 'Acción inválida.')
        return redirect('pagos_pendientes')

    # Solo se procesa si sigue pendiente; el filtro por estado evita que dos requests lo procesen a la vez.
    with transaction.atomic():
        if not Pago.objects.filter(pk=pago.pk, estado='pendiente').update(estado=estados[accion]):
            messages.error(request, 'Este pago ya fue procesado.')
            return redirect('pagos_pendientes')
        if accion == 'validar':
            pago.estado = 'validado'
            imputar_pago(pago)

    if accion == 'validar':
        messages.success(request, f'Pago de {pago.detalle_liquidacion.unidad_funcional} validado.')
    else:
        messages.error(request, f'Pago de {pago.detalle_liquidacion.unidad_funcional} rechazado. La deuda vuelve a estar activa.')
    return redirect('pagos_pendientes')




@login_required
@permission_required('consorcios.view_consorcio', raise_exception=True)
def descargar_resumen_uf(request, detalle_id):
    detalle = get_object_or_404(
        DetalleLiquidacionUF.objects.select_related(
            'liquidacion__consorcio',
            'unidad_funcional__propietario__usuario',
        ),
        pk=detalle_id,
    )
    liquidacion_permitida(request, detalle.liquidacion_id)
    pdf = generar_resumen_uf_pdf(detalle)
    respuesta = HttpResponse(pdf, content_type='application/pdf')
    respuesta['Content-Disposition'] = content_disposition_header(
        True,
        f'resumen-{detalle.unidad_funcional.pk}-{detalle.liquidacion.periodo}.pdf',
    )
    return respuesta

@login_required
@permission_required('consorcios.view_consorcio', raise_exception=True)
def servicios_recurrentes(request):
    """
    Alta, edición, pausa y baja de los servicios recurrentes de un consorcio.
    Los servicios se proponen solos en Generar Liquidación cuando corresponde.
    """
    consorcios = consorcios_permitidos(request.user).order_by('nombre')
    consorcio_id = request.POST.get('consorcio') or request.GET.get('consorcio', '')
    consorcio = consorcios.filter(pk=consorcio_id).first() if consorcio_id.isdecimal() else None
    if consorcio_id and not consorcio:
        messages.error(request, 'No tenés acceso a ese consorcio.')
        return redirect('servicios_recurrentes')

    formulario = None
    if request.method == 'POST' and consorcio:
        accion = request.POST.get('accion', '')
        servicio = None
        if accion in ('editar', 'pausar', 'borrar'):
            servicio = get_object_or_404(ServicioRecurrente, pk=request.POST.get('servicio_id', ''), consorcio=consorcio)
        if accion in ('crear', 'editar'):
            formulario = FormularioServicioRecurrente(request.POST, instance=servicio, consorcio=consorcio)
            if formulario.is_valid():
                servicio = formulario.save()
                messages.success(request, f"Servicio '{servicio.concepto}' guardado.")
                return redirect(f"{reverse('servicios_recurrentes')}?consorcio={consorcio.pk}")
            messages.error(request, 'Revisá los datos del servicio.')
        elif accion == 'pausar':
            servicio.activo = not servicio.activo
            servicio.save(update_fields=['activo'])
            estado = 'reactivado' if servicio.activo else 'pausado'
            messages.success(request, f"Servicio '{servicio.concepto}' {estado}.")
            return redirect(f"{reverse('servicios_recurrentes')}?consorcio={consorcio.pk}")
        elif accion == 'borrar':
            servicio.delete()
            messages.success(request, f"Servicio '{servicio.concepto}' eliminado.")
            return redirect(f"{reverse('servicios_recurrentes')}?consorcio={consorcio.pk}")

    servicios = []
    columnas = []
    if consorcio:
        hoy = date.today().strftime('%Y-%m')
        servicios = list(consorcio.servicios_recurrentes.select_related('columna__rubro'))
        for servicio in servicios:
            servicio.proximo = servicio.proximo_periodo(hoy)
        columnas = GrupoProrrateo.objects.filter(consorcio=consorcio).select_related('rubro').order_by('rubro__nombre', 'codigo')
        if formulario is None:
            formulario = FormularioServicioRecurrente(consorcio=consorcio)

    return render(request, 'servicios_recurrentes.html', {
        'consorcios': consorcios,
        'consorcio': consorcio,
        'servicios': servicios,
        'columnas': columnas,
        'formulario': formulario,
        'frecuencias': ServicioRecurrente.FRECUENCIAS,
        'tipos': TipoGasto.choices,
    })
