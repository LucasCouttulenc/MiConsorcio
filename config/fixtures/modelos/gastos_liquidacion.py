from datetime import date, timedelta

from gastos.models import Liquidacion

from ..fixture import Fixture
from consorcios.models import Consorcio


class FixtureDeLiquidacion(Fixture):
    """Crea dos liquidaciones vencidas por consorcio para que Morosidad tenga datos."""

    def __init__(self):
        super().__init__(Liquidacion)

    def campos(self):
        consorcios = self.administrador.obtener_ids(Consorcio)
        hoy = date.today()
        vencimientos = [hoy - timedelta(days=dias) for dias in (75, 40)]
        periodos = [(vencimiento.strftime('%Y-%m'), vencimiento) for vencimiento in vencimientos]

        return [
            {
                'consorcio_id': consorcio_id,
                'periodo': periodo,
                'fecha_cierre': str(vencimiento - timedelta(days=10)),
                'fecha_vencimiento_1': str(vencimiento),
                'total_ordinario': '0.00',
                'total_extraordinario': '0.00',
                'cerrada': True,
                'datos_borrador': {},
            }
            for consorcio_id in consorcios
            for periodo, vencimiento in periodos
        ]
