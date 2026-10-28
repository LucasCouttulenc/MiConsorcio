"""
Convenios de pago: el administrador refinancia la deuda vencida de una UF en cuotas
y el propietario sigue sus cuotas desde el portal.
"""
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render

from consorcios.models import UnidadFuncional
from usuarios.models import Propietario
from consorcios.permisos import consorcio_activo

from .models import ConvenioPago, Liquidacion, crear_convenio, deuda_para_convenio
from .views import CLAVE_UNIDAD_PROPIETARIO, periodo_legible, unidad_recordada

CUOTAS_MAXIMAS = 36


def siguiente_periodo(periodo):
    anio, mes = map(int, periodo.split('-'))
    return f'{anio + mes // 12}-{mes % 12 + 1:02d}'


def periodos_para_empezar(consorcio, cantidad=3):
    """Próximos períodos sin liquidar, para elegir en cuál se cobra la primera cuota."""
    ultima = Liquidacion.objects.filter(consorcio=consorcio, cerrada=True).order_by('-periodo').first()
    periodo = siguiente_periodo(ultima.periodo) if ultima else date.today().strftime('%Y-%m')
    periodos = []
    for _ in range(cantidad):
        periodos.append((periodo, periodo_legible(periodo)))
        periodo = siguiente_periodo(periodo)
    return periodos


def convenio_actual(unidad):
    """El convenio vigente de la UF o, si no hay, el último que tuvo."""
    convenios = unidad.convenios.prefetch_related(
        'cuotas__detalle_liquidacion__liquidacion__consorcio', 'cuotas__detalle_liquidacion__imputaciones__pago',
        'periodos_incluidos__liquidacion',
    )
    convenio = convenios.filter(estado='vigente').first() or convenios.first()
    if convenio:
        convenio.actualizar_estado()
        # Las cuotas sin liquidar van una por mes, a partir de la última liquidada (o del primer período).
        cobradas = [cuota.periodo for cuota in convenio.cuotas.all() if cuota.periodo]
        previsto = siguiente_periodo(max(cobradas)) if cobradas else convenio.periodo_inicio
        convenio.filas_cuotas = []
        for cuota in convenio.cuotas.all():
            periodo = cuota.periodo
            if not periodo:
                periodo, previsto = previsto, siguiente_periodo(previsto)
            convenio.filas_cuotas.append({
                'cuota': cuota, 'estado': cuota.estado, 'periodo': periodo_legible(periodo),
                'liquidada': bool(cuota.detalle_liquidacion_id),
            })
        convenio.periodos_label = [periodo_legible(d.liquidacion.periodo) for d in convenio.periodos_incluidos.all()]
        convenio.periodo_inicio_label = periodo_legible(convenio.periodo_inicio)
    return convenio


def _decimal(valor, defecto):
    try:
        return Decimal(str(valor).replace(',', '.')) if str(valor).strip() else defecto
    except InvalidOperation:
        return None


def _entero(valor, defecto):
    return int(valor) if str(valor).strip().isdecimal() else (defecto if not str(valor).strip() else None)


@login_required
@permission_required('consorcios.change_consorcio', raise_exception=True)
def armar_convenio(request, unidad_id):
    consorcio = consorcio_activo(request)
    if not consorcio:
        messages.error(request, "Seleccioná un consorcio primero.")
        return redirect('bienvenida')
    unidad = get_object_or_404(
        UnidadFuncional.objects.select_related('consorcio', 'propietario__usuario'), pk=unidad_id, consorcio=consorcio,
    )
    if unidad.convenios.filter(estado='vigente').exists():
        messages.info(request, "Esta unidad ya tiene un convenio vigente.")
        return redirect('morosidad_unidad', unidad_id=unidad.pk)

    hoy = date.today()
    deuda = deuda_para_convenio(unidad, hoy)
    if not deuda:
        messages.info(request, "Esta unidad no tiene deuda para refinanciar.")
        return redirect('morosidad_unidad', unidad_id=unidad.pk)
    periodos = periodos_para_empezar(consorcio)
    valores = {'cantidad_cuotas': '6', 'interes_porcentaje': '0', 'cuotas_para_caducidad': '2',
               'periodo_inicio': periodos[0][0]}
    errores = {}

    if request.method == 'POST':
        valores = {clave: request.POST.get(clave, '').strip() for clave in valores}
        cuotas = _entero(valores['cantidad_cuotas'], None)
        if not cuotas or not 1 <= cuotas <= CUOTAS_MAXIMAS:
            errores['cantidad_cuotas'] = f'Elegí entre 1 y {CUOTAS_MAXIMAS} cuotas.'
        interes = _decimal(valores['interes_porcentaje'], Decimal('0'))
        if interes is None or not Decimal('0') <= interes <= Decimal('100'):
            errores['interes_porcentaje'] = 'Ingresá un porcentaje entre 0 y 100.'
        caducidad = _entero(valores['cuotas_para_caducidad'], 2)
        if not caducidad or caducidad > CUOTAS_MAXIMAS:
            errores['cuotas_para_caducidad'] = 'Ingresá cuántas cuotas impagas hacen caer el convenio (1 o más).'
        if valores['periodo_inicio'] not in dict(periodos):
            errores['periodo_inicio'] = 'Elegí un período de la lista.'
        if not errores:
            crear_convenio(unidad, cuotas, valores['periodo_inicio'], interes, caducidad, hoy)
            messages.success(request, f'Convenio creado: {cuotas} cuota{"s" if cuotas > 1 else ""}. '
                                      'La primera se suma a la liquidación de '
                                      f'{periodo_legible(valores["periodo_inicio"])}.')
            return redirect('morosidad_unidad', unidad_id=unidad.pk)

    capital = sum((fila['capital'] for fila in deuda), Decimal('0'))
    intereses = sum((fila['interes'] for fila in deuda), Decimal('0'))
    return render(request, 'armar_convenio.html', {
        'unidad': unidad, 'hoy': hoy,
        'periodos_deuda': [dict(fila, label=periodo_legible(fila['detalle'].liquidacion.periodo)) for fila in deuda],
        'capital': capital, 'intereses': intereses, 'deuda': capital + intereses,
        'periodos': periodos, 'valores': valores, 'errores': errores,
        'tasa': consorcio.tasa_interes_mensual,
    })


@login_required
def mi_convenio(request):
    propietario = get_object_or_404(Propietario, usuario=request.user)
    unidades = UnidadFuncional.objects.filter(propietario=propietario).select_related('consorcio')
    unidad = unidades.filter(pk=request.GET.get('unidad')).first() if request.GET.get('unidad', '').isdecimal() else None
    unidad = unidad or unidad_recordada(request, propietario) or unidades.first()
    if unidad:
        request.session[CLAVE_UNIDAD_PROPIETARIO] = unidad.pk
    return render(request, 'mi_convenio.html', {
        'unidad': unidad,
        'convenio': convenio_actual(unidad) if unidad else None,
    })
