from ..fixture import Fixture
from consorcios.models import Rubro, Consorcio

RUBRO_REMUNERACIONES = 'REMUNERACIONES AL PERSONAL'
RUBRO_SERVICIOS_PUBLICOS = 'SERVICIOS PÚBLICOS'
RUBRO_MANTENIMIENTO = 'MANTENIMIENTO DE PARTES COMUNES'
RUBRO_ADMINISTRACION = 'GASTOS DE ADMINISTRACIÓN'

RUBROS = [
    RUBRO_REMUNERACIONES,
    RUBRO_SERVICIOS_PUBLICOS,
    RUBRO_MANTENIMIENTO,
    RUBRO_ADMINISTRACION,
]


class FixtureDeRubro(Fixture):
    def __init__(self):
        super().__init__(Rubro)

    def campos(self):
        return [
            {'consorcio': consorcio, 'nombre': nombre}
            for consorcio in self.administrador.obtener_ids(Consorcio)
            for nombre in RUBROS
        ]