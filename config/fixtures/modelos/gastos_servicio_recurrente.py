from ..fixture import Fixture
from .escenario_gastos import DEPENDENCIAS_ESCENARIO, a_json, obtener_escenario
from gastos.models import ServicioRecurrente

CAMPOS = ('consorcio', 'concepto', 'proveedor', 'columna', 'tipo', 'monto_sugerido',
          'frecuencia_meses', 'periodo_inicio', 'periodo_fin', 'activo')


class FixtureDeServicioRecurrente(Fixture):
    """Abonos mensuales, servicios trimestrales y semestrales, uno anual a futuro y uno dado de baja."""

    dependencias_extra = DEPENDENCIAS_ESCENARIO

    def __init__(self):
        super().__init__(ServicioRecurrente)

    def campos(self):
        escenario = obtener_escenario(self.administrador)
        return [{campo: a_json(servicio[campo]) for campo in CAMPOS} for servicio in escenario.servicios]
