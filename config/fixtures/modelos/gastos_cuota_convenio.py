from ..fixture import Fixture
from .escenario_gastos import DEPENDENCIAS_ESCENARIO, a_json, id_detalle, obtener_escenario
from gastos.models import ConvenioPago, CuotaConvenio


class FixtureDeCuotaConvenio(Fixture):
    """Cuotas de cada convenio. Las ya liquidadas apuntan a la expensa en la que se cobraron."""

    dependencias_extra = DEPENDENCIAS_ESCENARIO

    def __init__(self):
        super().__init__(CuotaConvenio)

    def campos(self):
        adm = self.administrador
        escenario = obtener_escenario(adm)
        resultado = []

        for cuota in escenario.cuotas:
            detalle = None
            if cuota['periodo']:
                detalle = id_detalle(adm, cuota['consorcio'], cuota['periodo'], cuota['unidad_funcional'])

            resultado.append({
                'convenio': adm.obtener_id(ConvenioPago, unidad_funcional=cuota['unidad_funcional']),
                'numero': cuota['numero'],
                'monto': a_json(cuota['monto']),
                'detalle_liquidacion': detalle,
            })

        return resultado
