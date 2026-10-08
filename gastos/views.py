import json
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import content_disposition_header
from django.views.decorators.http import require_POST

from usuarios.models import Propietario
from .forms import FormularioPago
from consorcios.models import Consorcio, GrupoProrrateo
from .models import Gasto, Liquidacion, TipoGasto, Pago, DetalleLiquidacionUF
from .pdf import generar_pdf_liquidacion
from .services import procesar_liquidacion_periodo
from consorcios.alicuotas import consorcio_tiene_alicuotas_validas, suma_alicuotas

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
    consorcios = consorcios_permitidos(request.user).order_by('nombre')

    # Precargamos rubros y columnas para JS
    rubros_por_consorcio = {}
    columnas_por_rubro = {}

    for c in consorcios:
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
            if monto <= 0 or monto.as_tuple().exponent < -2:
                raise ValueError('Los montos deben ser positivos y tener hasta dos decimales.')
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
def finalizar_liquidacion(request):
    try:
        with transaction.atomic():
            liquidacion = guardar_borrador(request, finalizar=True)
            datos = liquidacion.datos_borrador
            liquidacion.gastos_cargados.all().delete()
            columnas = {str(g.pk): g for g in GrupoProrrateo.objects.filter(consorcio=liquidacion.consorcio)}
            for posicion, gasto in enumerate(datos['gastos']):
                columna = columnas.get(str(gasto.get('grupo', '')))
                if not columna:
                    raise ValueError('Un gasto usa una columna que no pertenece al consorcio.')
                Gasto.objects.create(
                    liquidacion=liquidacion, consorcio=liquidacion.consorcio,
                    periodo=liquidacion.periodo, fecha_comprobante=date.today(),
                    posicion=posicion, concepto=str(gasto['concepto']).strip()[:200],
                    tipo=gasto['tipo'],
                    grupo=columna, monto=Decimal(str(gasto['monto']).replace(',', '.')))
            procesar_liquidacion_periodo(liquidacion)
            liquidacion.documento = generar_pdf_liquidacion(liquidacion)
            liquidacion.cerrada = True
            liquidacion.save(update_fields=['documento', 'cerrada', 'actualizada'])
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
    tipos_permitidos = {'application/pdf', 'image/jpeg', 'image/png'}
    if archivo.content_type not in tipos_permitidos:
        messages.error(request, 'El comprobante debe ser PDF, JPG o PNG.')
        return redirect('detalle_liquidacion', liquidacion_id=gasto.liquidacion_id)
    if archivo.size > 5 * 1024 * 1024:
        messages.error(request, 'El comprobante no puede superar los 5 MB.')
        return redirect('detalle_liquidacion', liquidacion_id=gasto.liquidacion_id)
    gasto.comprobante = archivo
    gasto.save(update_fields=['comprobante'])
    messages.success(request, 'Comprobante adjuntado.')
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


@login_required
def mis_expensas(request):
    """Muestra al propietario sus liquidaciones y el estado de deuda."""
    propietario = get_object_or_404(Propietario, usuario=request.user)
    
    # Traemos todas las expensas de sus departamentos
    detalles = DetalleLiquidacionUF.objects.filter(
        unidad_funcional__propietario=propietario
    ).order_by('-liquidacion__periodo')
    
    return render(request, 'mis_expensas.html', {'detalles': detalles})

@login_required
def registrar_pago(request, detalle_id):
    """Procesa el formulario cuando el propietario sube un comprobante."""
    detalle = get_object_or_404(DetalleLiquidacionUF, pk=detalle_id)
    
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
        monto_sugerido = detalle.deuda_total_actualizada
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
        
    accion = request.POST.get('accion')
    if accion == 'validar':
        pago.estado = 'validado'
        messages.success(request, f'Pago de {pago.detalle_liquidacion.unidad_funcional} validado.')
    elif accion == 'rechazar':
        pago.estado = 'rechazado'
        messages.error(request, f'Pago de {pago.detalle_liquidacion.unidad_funcional} rechazado. La deuda vuelve a estar activa.')
        
    pago.save()
    return redirect('pagos_pendientes')