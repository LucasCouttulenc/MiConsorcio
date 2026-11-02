from ..fixture import Fixture
from .escenario_gastos import DEPENDENCIAS_ESCENARIO, a_json, obtener_escenario
from gastos.models import ConvenioPago

CAMPOS = ('unidad_funcional', 'fecha_alta', 'capital', 'intereses', 'interes_porcentaje',
          'cantidad_cuotas', 'cuotas_para_caducidad', 'periodo_inicio', 'estado')


class FixtureDeConvenioPago(Fixture):
    """Refinanciaciones vigentes de deuda vencida, con capital e intereses calculados como en crear_convenio."""

    dependencias_extra = DEPENDENCIAS_ESCENARIO

    def __init__(self):
        super().__init__(ConvenioPago)

    def campos(self):
        escenario = obtener_escenario(self.administrador)
        return [{campo: a_json(convenio[campo]) for campo in CAMPOS} for convenio in escenario.convenios]
