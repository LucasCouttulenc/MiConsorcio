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

from consorcios.models import Consorcio, GrupoProrrateo
from .models import Gasto, Liquidacion, TipoGasto
from .services import generar_pdf_liquidacion, procesar_liquidacion_periodo


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
    consorcios = consorcios_permitidos(request.user).prefetch_related('grupos_prorrateo').order_by('nombre')
    liquidacion = liquidacion_permitida(request, liquidacion_id) if liquidacion_id else None
    if liquidacion and liquidacion.cerrada:
        return redirect('detalle_liquidacion', liquidacion_id=liquidacion.pk)
    consorcio_id = request.GET.get('consorcio', '')
    if consorcio_id and (not consorcio_id.isdecimal() or not consorcios.filter(pk=consorcio_id).exists()):
        raise Http404('Consorcio no disponible')
    return render(request, 'generar_liquidacion.html', {
        'consorcios': consorcios, 'liquidacion': liquidacion,
        'datos_iniciales': liquidacion.datos_borrador if liquidacion else {},
        'consorcio_inicial': liquidacion.consorcio_id if liquidacion else consorcio_id,
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
        grupos_nuevos = json.loads(request.POST.get('grupos_nuevos', '[]'))
        subtipos = json.loads(request.POST.get('subtipos', '[]'))
    except json.JSONDecodeError as exc:
        raise ValueError('Los gastos enviados no tienen un formato válido.') from exc
    if not all(isinstance(item, list) for item in (gastos, grupos_nuevos, subtipos)) or len(gastos) > 300:
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
                raise ValueError('Completá concepto, tipo y grupo en cada gasto.')
    if finalizar and not gastos:
        raise ValueError('Agregá al menos un gasto antes de finalizar.')
    administracion = {campo: request.POST.get(campo, '').strip()[:200] for campo in (
        'admin_razon', 'admin_nombre', 'admin_domicilio', 'admin_fiscal',
        'admin_cuit', 'admin_rpa', 'admin_telefono', 'admin_mail')}
    return consorcio, periodo, fecha_cierre, fecha_vencimiento, {
        'consorcio': consorcio.pk, 'mes': f'{int(mes):02d}', 'anio': str(int(anio)),
        'fecha_cierre': cierre, 'fecha_vencimiento_1': vencimiento,
        'administracion': administracion, 'gastos': gastos,
        'grupos_nuevos': grupos_nuevos, 'subtipos': subtipos,
    }


def guardar_borrador(request, finalizar=False):
    consorcio, periodo, cierre, vencimiento, datos = leer_datos(request, finalizar)
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
            grupos = {str(g.pk): g for g in GrupoProrrateo.objects.filter(consorcio=liquidacion.consorcio)}
            for nuevo in datos['grupos_nuevos']:
                if not isinstance(nuevo, dict):
                    raise ValueError('Un grupo nuevo no es válido.')
                codigo = str(nuevo.get('codigo', '')).strip()[:10]
                nombre = str(nuevo.get('nombre', '')).strip()[:100]
                if not codigo or not nombre:
                    raise ValueError('Completá el nombre de los grupos nuevos.')
                grupo, _ = GrupoProrrateo.objects.get_or_create(
                    consorcio=liquidacion.consorcio, codigo=codigo, defaults={'nombre': nombre})
                grupos[str(nuevo.get('id', ''))] = grupo
            liquidacion.gastos_cargados.all().delete()
            for posicion, gasto in enumerate(datos['gastos']):
                grupo = grupos.get(str(gasto.get('grupo', '')))
                if not grupo:
                    raise ValueError('Un gasto usa un grupo que no pertenece al consorcio.')
                Gasto.objects.create(
                    liquidacion=liquidacion, consorcio=liquidacion.consorcio,
                    periodo=liquidacion.periodo, fecha_comprobante=date.today(),
                    posicion=posicion, concepto=str(gasto['concepto']).strip()[:200],
                    tipo=gasto['tipo'], subtipo=str(gasto.get('subtipo', ''))[:100],
                    grupo=grupo, monto=Decimal(str(gasto['monto']).replace(',', '.')))
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
