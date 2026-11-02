from ..fixture import Fixture
from .escenario_gastos import DEPENDENCIAS_ESCENARIO, a_json, id_liquidacion, obtener_escenario
from gastos.models import Gasto, ServicioRecurrente


class FixtureDeGasto(Fixture):
    """
    Gastos de cada liquidación cerrada: sueldos, servicios, abonos recurrentes, reparaciones y obra.
    Los que se pagan después de hoy quedan impagos y fuera de caja.
    """

    dependencias_extra = DEPENDENCIAS_ESCENARIO

    def __init__(self):
        super().__init__(Gasto)

    def campos(self):
        adm = self.administrador
        escenario = obtener_escenario(adm)
        resultado = []

        for gasto in escenario.gastos:
            servicio = None
            if gasto['servicio']:
                servicio = adm.obtener_id(ServicioRecurrente, consorcio=gasto['consorcio'], concepto=gasto['servicio'])

            resultado.append({
                'consorcio': gasto['consorcio'],
                'concepto': gasto['concepto'],
                'monto': a_json(gasto['monto']),
                'tipo': gasto['tipo'],
                'clase': gasto['clase'],
                'pagado': gasto['pagado'],
                'en_caja': gasto['en_caja'],
                'grupo': gasto['grupo'],
                'periodo': gasto['periodo'],
                'fecha_comprobante': a_json(gasto['fecha_comprobante']),
                'liquidacion': id_liquidacion(adm, gasto['consorcio'], gasto['periodo']),
                'posicion': gasto['posicion'],
                'comprobante_visible': True,
                'servicio': servicio,
            })

        return resultado