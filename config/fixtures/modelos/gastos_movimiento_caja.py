from ..fixture import Fixture
from .escenario_gastos import DEPENDENCIAS_ESCENARIO, a_json, obtener_escenario
from gastos.models import MovimientoCaja

CAMPOS = ('consorcio', 'fecha', 'concepto', 'monto', 'tipo', 'medio_pago')


class FixtureDeMovimientoCaja(Fixture):
    """Saldo inicial, egreso por cada gasto pagado e ingreso por cada pago validado."""

    dependencias_extra = DEPENDENCIAS_ESCENARIO

    def __init__(self):
        super().__init__(MovimientoCaja)

    def campos(self):
        escenario = obtener_escenario(self.administrador)
        return [{campo: a_json(m[campo]) for campo in CAMPOS} for m in escenario.movimientos]
