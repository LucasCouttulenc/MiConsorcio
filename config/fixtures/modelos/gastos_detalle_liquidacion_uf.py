from ..fixture import Fixture
from .escenario_gastos import DEPENDENCIAS_ESCENARIO, a_json, id_liquidacion, obtener_escenario
from gastos.models import ConvenioPago, DetalleLiquidacionUF

MONTOS = ('alicuota', 'monto_ordinario', 'monto_extraordinario', 'monto_fondo_reserva',
          'monto_convenio', 'monto_total')


class FixtureDeDetalleLiquidacionUf(Fixture):
    """Expensa de cada UF en cada liquidación: suma de lo que le tocó de cada gasto, fondo y cuota de convenio."""

    dependencias_extra = DEPENDENCIAS_ESCENARIO

    def __init__(self):
        super().__init__(DetalleLiquidacionUF)

    def campos(self):
        adm = self.administrador
        escenario = obtener_escenario(adm)
        resultado = []

        for detalle in escenario.detalles:
            convenio = None
            if detalle['convenio']:
                convenio = adm.obtener_id(ConvenioPago, unidad_funcional=detalle['convenio'])

            resultado.append({
                'liquidacion': id_liquidacion(adm, detalle['consorcio'], detalle['periodo']),
                'unidad_funcional': detalle['unidad_funcional'],
                **{campo: a_json(detalle[campo]) for campo in MONTOS},
                'convenio': convenio,
            })

        return resultado
