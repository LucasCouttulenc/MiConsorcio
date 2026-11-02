from ..fixture import Fixture
from .escenario_gastos import DEPENDENCIAS_ESCENARIO, a_json, obtener_escenario
from gastos.models import Novedad

CAMPOS = ('propietario', 'consorcio', 'unidad_funcional', 'tipo', 'texto', 'detalle', 'creada', 'leida_en')


class FixtureDeNovedad(Fixture):
    """Avisos del consorcio, obra en curso, liquidación disponible y resultado de los pagos recientes."""

    dependencias_extra = DEPENDENCIAS_ESCENARIO

    def __init__(self):
        super().__init__(Novedad)

    def campos(self):
        escenario = obtener_escenario(self.administrador)
        return [
            {**{campo: a_json(novedad[campo]) for campo in CAMPOS}, 'url': ''}
            for novedad in escenario.novedades
        ]
