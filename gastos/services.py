from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from consorcios.models import UnidadFuncional, GrupoProrrateo, CoeficienteUF
from .models import Gasto, Liquidacion, DetalleLiquidacionUF, TipoGasto

@transaction.atomic
def procesar_liquidacion_periodo(consorcio, periodo, fecha_vencimiento_1):
    gastos = Gasto.objects.filter(consorcio=consorcio, periodo=periodo)
    grupos = GrupoProrrateo.objects.filter(consorcio=consorcio)
    
    totales_ordinarios_grupo = {}
    totales_extraordinarios_grupo = {}

    total_ordinario_general = Decimal('0.00')
    total_extraordinario_general = Decimal('0.00')

    for grupo in grupos:
        ord_monto = gastos.filter(tipo=TipoGasto.ORDINARIO, grupo=grupo).aggregate(s=Sum('monto'))['s'] or Decimal('0.00')
        ext_monto = gastos.filter(tipo=TipoGasto.EXTRAORDINARIO, grupo=grupo).aggregate(s=Sum('monto'))['s'] or Decimal('0.00')

        totales_ordinarios_grupo[grupo.id] = ord_monto
        totales_extraordinarios_grupo[grupo.id] = ext_monto

        total_ordinario_general += ord_monto
        total_extraordinario_general += ext_monto

    liquidacion, _ = Liquidacion.objects.update_or_create(
        consorcio=consorcio,
        periodo=periodo,
        defaults={
            'fecha_vencimiento_1': fecha_vencimiento_1,
            'total_ordinario': total_ordinario_general,
            'total_extraordinario': total_extraordinario_general,
            'cerrada': True,
        }
    )

    liquidacion.detalles_uf.all().delete()

    unidades = UnidadFuncional.objects.filter(consorcio=consorcio)
    detalles = []

    for uf in unidades:
        monto_ord_uf = Decimal('0.00')
        monto_ext_uf = Decimal('0.00')

        coeficientes = CoeficienteUF.objects.filter(unidad_funcional=uf).select_related('grupo')
        coef_dict = {c.grupo_id: c.porcentaje for c in coeficientes}

        for grupo in grupos:
            porcentaje = coef_dict.get(grupo.id, Decimal('0.0000'))
            factor = porcentaje / Decimal('100.00')

            monto_ord_uf += totales_ordinarios_grupo[grupo.id] * factor
            monto_ext_uf += totales_extraordinarios_grupo[grupo.id] * factor

        monto_total_uf = monto_ord_uf + monto_ext_uf

        detalles.append(
            DetalleLiquidacionUF(
                liquidacion=liquidacion,
                unidad_funcional=uf,
                monto_ordinario=round(monto_ord_uf, 2),
                monto_extraordinario=round(monto_ext_uf, 2),
                monto_total=round(monto_total_uf, 2)
            )
        )

    DetalleLiquidacionUF.objects.bulk_create(detalles)
    return liquidacion