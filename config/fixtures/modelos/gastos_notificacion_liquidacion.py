from ..fixture import Fixture
from .escenario_gastos import DEPENDENCIAS_ESCENARIO, a_json, id_detalle, obtener_escenario
from gastos.models import NotificacionLiquidacion


class FixtureDeNotificacionLiquidacion(Fixture):
    """Una notificación por expensa. Las viejas están casi todas leídas; las del último mes, no."""

    dependencias_extra = DEPENDENCIAS_ESCENARIO

    def __init__(self):
        super().__init__(NotificacionLiquidacion)

    def campos(self):
        adm = self.administrador
        escenario = obtener_escenario(adm)
        return [
            {
                'propietario': n['propietario'],
                'detalle_liquidacion': id_detalle(adm, n['consorcio'], n['periodo'], n['unidad_funcional']),
                'creada': a_json(n['creada']),
                'leida_en': a_json(n['leida_en']),
            }
            for n in escenario.notificaciones
        ]
