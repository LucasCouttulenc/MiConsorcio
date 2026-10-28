from gastos.models import DetalleLiquidacionUF, Liquidacion
from consorcios.models import UnidadFuncional

from ..fixture import Fixture


class FixtureDeDetalleLiquidacionUf(Fixture):
    """Deja dos unidades con deuda y distintos niveles de atraso en cada consorcio."""

    def __init__(self):
        super().__init__(DetalleLiquidacionUF)

    def campos(self):
        liquidaciones = self.administrador._diccionario_fixtures.get(Liquidacion, [])
        unidades = self.administrador._diccionario_fixtures.get(UnidadFuncional, [])
        unidades_por_consorcio = {}
        for registro in unidades:
            unidades_por_consorcio.setdefault(registro['fields']['consorcio_id'], []).append(registro)

        periodos_por_consorcio = {}
        for registro in liquidaciones:
            campos = registro['fields']
            periodos_por_consorcio.setdefault(campos['consorcio_id'], {})[campos['periodo']] = registro['pk']

        resultado = []
        for consorcio_id, periodos in periodos_por_consorcio.items():
            ufs = sorted(unidades_por_consorcio.get(consorcio_id, []), key=lambda uf: uf['fields']['piso'])
            if len(ufs) < 2:
                continue

            periodo_mas_antiguo, periodo_reciente = sorted(periodos)
            for periodo, seleccion in (
                (periodo_mas_antiguo, ufs[:1]),
                (periodo_reciente, ufs[:2]),
            ):
                total_liquidacion = 0
                for indice, uf in enumerate(seleccion):
                    monto = '86000.00' if indice == 0 else '72000.00'
                    total_liquidacion += int(float(monto))
                    resultado.append({
                        'liquidacion_id': periodos[periodo],
                        'unidad_funcional_id': uf['pk'],
                        'alicuota': uf['fields']['alicuota'],
                        'monto_ordinario': monto,
                        'monto_extraordinario': '0.00',
                        'monto_fondo_reserva': '0.00',
                        'monto_convenio': '0.00',
                        'monto_total': monto,
                    })
                liquidacion = next(
                    reg for reg in liquidaciones if reg['pk'] == periodos[periodo]
                )
                liquidacion['fields']['total_ordinario'] = f'{total_liquidacion:.2f}'

        return resultado
