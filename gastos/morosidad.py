"""
Morosidad: cuánto debe cada UF de un consorcio (capital + intereses) y desde cuándo.
Usa los mismos cálculos que el portal del propietario, así los números coinciden.
"""
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render

# Agregamos Consorcio acá
from consorcios.models import UnidadFuncional, Consorcio

from .models import DetalleLiquidacionUF, Liquidacion, Pago
from .views import consorcios_permitidos, periodo_legible

FILTROS = {
    'con_deuda': ('Con deuda', lambda fila: fila['total'] > 0),
    'mas_30': ('Más de 30 días', lambda fila: fila['dias_atraso'] > 30),
    'mas_60': ('Más de 60 días', lambda fila: fila['dias_atraso'] > 60),
    'todas': ('Todas', lambda fila: True),
}


def deuda_de_unidad(unidad, detalles, hoy):
    """Resumen de deuda de una UF a partir de sus liquidaciones cerradas (ordenadas por período)."""
    impagos = [detalle for detalle in detalles if not detalle.esta_pagado]
    capital = sum((detalle.deuda_total_actualizada for detalle in impagos), Decimal('0'))
    intereses = sum((detalle.interes(hoy) for detalle in impagos), Decimal('0'))
    vencidos = [d.liquidacion.fecha_vencimiento_1 for d in impagos
                if d.liquidacion.fecha_vencimiento_1 and d.liquidacion.fecha_vencimiento_1 < hoy]
    return {
        'unidad': unidad,
        'impagos': impagos,
        'periodos_impagos': len(impagos),
        'desde': periodo_legible(impagos[0].liquidacion.periodo) if impagos else '',
        'capital': capital,
        'intereses': intereses,
        'total': capital + intereses,
        'dias_atraso': (hoy - min(vencidos)).days if vencidos else 0,
    }


def nivel_atraso(dias):
    if dias <= 0:
        return 'sin-vencer'
    if dias <= 30:
        return 'hasta-30'
    if dias <= 60:
        return 'hasta-60'
    return 'mas-60'


def detalles_cerrados(unidades):
    return DetalleLiquidacionUF.objects.filter(
        unidad_funcional__in=unidades, liquidacion__cerrada=True,
    ).select_related('liquidacion__consorcio').prefetch_related('imputaciones__pago', 'pagos').order_by('liquidacion__periodo')


@login_required
@permission_required('consorcios.view_consorcio', raise_exception=True)
def morosidad(request):
    consorcio_id = request.session.get('consorcio_activo_id')
    if not consorcio_id:
        messages.error(request, "Seleccioná un consorcio primero.")
        return redirect('bienvenida')
    
    consorcio = get_object_or_404(Consorcio, id=consorcio_id)

    hoy = date.today()
    unidades = list(UnidadFuncional.objects.filter(consorcio=consorcio).select_related('propietario__usuario'))
    por_unidad = {unidad.pk: [] for unidad in unidades}
    for detalle in detalles_cerrados(unidades):
        por_unidad[detalle.unidad_funcional_id].append(detalle)
        
    filas = []
    for unidad in unidades:
        fila = deuda_de_unidad(unidad, por_unidad[unidad.pk], hoy)
        fila['nivel'] = nivel_atraso(fila['dias_atraso'])
        fila['pagos_en_revision'] = sum(
            1 for detalle in por_unidad[unidad.pk] for pago in detalle.pagos.all() if pago.estado == 'pendiente'
        )
        filas.append(fila)
    filas.sort(key=lambda fila: (-fila['total'], fila['unidad'].piso, fila['unidad'].departamento))

    filtro = request.GET.get('filtro', 'con_deuda')
    if filtro not in FILTROS:
        filtro = 'con_deuda'
    visibles = [fila for fila in filas if FILTROS[filtro][1](fila)]

    # Cuánto de la última liquidación ya entró como capital cancelado.
    ultima = Liquidacion.objects.filter(consorcio=consorcio, cerrada=True).order_by('-periodo').first()
    cobrado = None
    if ultima:
        detalles_ultima = [d for detalles in por_unidad.values() for d in detalles if d.liquidacion_id == ultima.pk]
        liquidado = sum((d.monto_total for d in detalles_ultima), Decimal('0'))
        if liquidado:
            cobrado = round(sum((d.total_pagado for d in detalles_ultima), Decimal('0')) * 100 / liquidado)

    return render(request, 'morosidad.html', {
        'consorcio': consorcio, 'hoy': hoy,
        'filas': visibles, 'filtro': filtro,
        'filtros': [(clave, nombre, sum(1 for fila in filas if regla(fila))) for clave, (nombre, regla) in FILTROS.items()],
        'total_capital': sum((fila['capital'] for fila in visibles), Decimal('0')),
        'total_intereses': sum((fila['intereses'] for fila in visibles), Decimal('0')),
        'total_deuda': sum((fila['total'] for fila in visibles), Decimal('0')),
        'deuda_consorcio': sum((fila['total'] for fila in filas), Decimal('0')),
        'intereses_consorcio': sum((fila['intereses'] for fila in filas), Decimal('0')),
        'con_deuda': sum(1 for fila in filas if fila['total'] > 0),
        'con_deuda_30': sum(1 for fila in filas if fila['dias_atraso'] > 30),
        'cantidad_unidades': len(filas),
        'ultima': ultima, 'ultima_label': periodo_legible(ultima.periodo) if ultima else '', 'cobrado': cobrado,
    })


@login_required
@permission_required('consorcios.view_consorcio', raise_exception=True)
def morosidad_unidad(request, unidad_id):
    """Estado de cuenta de una UF para el administrador: deuda por período y movimientos."""
    consorcio_id = request.session.get('consorcio_activo_id')
    if not consorcio_id:
        messages.error(request, "Seleccioná un consorcio primero.")
        return redirect('bienvenida')

    # Filtramos por el consorcio activo para evitar que puedan ver UFs de otros consorcios por URL
    unidad = get_object_or_404(
        UnidadFuncional.objects.select_related('consorcio', 'propietario__usuario'),
        pk=unidad_id, consorcio_id=consorcio_id,
    )
    hoy = date.today()
    detalles = list(detalles_cerrados([unidad]))
    resumen = deuda_de_unidad(unidad, detalles, hoy)
    periodos = [{
        'detalle': detalle,
        'label': periodo_legible(detalle.liquidacion.periodo),
        'interes_devengado': detalle.interes_devengado(hoy),
        'meses': detalle.meses_de_atraso(hoy),
        'capital_pagado': detalle.total_pagado,
        'intereses_pagados': detalle.intereses_pagados,
        'adeuda': detalle.deuda_total_actualizada + detalle.interes(hoy),
    } for detalle in resumen['impagos']]

    movimientos = [{
        'fecha': detalle.liquidacion.fecha_cierre or detalle.liquidacion.fecha_emision,
        'titulo': f'Liquidación {periodo_legible(detalle.liquidacion.periodo)}',
        'monto': detalle.monto_total, 'tipo': 'liquidacion',
    } for detalle in detalles]
    pagos = Pago.objects.filter(detalle_liquidacion__unidad_funcional=unidad).exclude(estado='rechazado')
    movimientos += [{
        'fecha': pago.fecha_pago,
        'titulo': 'Pago validado' if pago.estado == 'validado' else 'Pago en revisión',
        'monto': pago.monto_pagado, 'tipo': pago.estado, 'pago': pago,
    } for pago in pagos]
    movimientos.sort(key=lambda movimiento: movimiento['fecha'], reverse=True)

    return render(request, 'morosidad_unidad.html', {
        'unidad': unidad,
        'resumen': resumen,
        'nivel': nivel_atraso(resumen['dias_atraso']),
        'periodos': periodos, 'movimientos': movimientos,
        'tasa': unidad.consorcio.tasa_interes_mensual,
    })