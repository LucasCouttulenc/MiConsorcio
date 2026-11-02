from ..fixture import Fixture
from .escenario_gastos import DEPENDENCIAS_ESCENARIO, a_json, id_detalle, id_pago, obtener_escenario
from gastos.models import ImputacionPago


class FixtureDeImputacionPago(Fixture):
    """
    Lo que haría imputar_pago con cada pago validado. Se cargan explícitas porque
    loaddata no llama a Pago.save() y por lo tanto no se imputa nada solo.
    """

    dependencias_extra = DEPENDENCIAS_ESCENARIO

    def __init__(self):
        super().__init__(ImputacionPago)

    def campos(self):
        adm = self.administrador
        escenario = obtener_escenario(adm)
        resultado = []

        for imputacion in escenario.imputaciones:
            consorcio = imputacion['consorcio']
            detalle = None
            if imputacion['detalle']:
                unidad_funcional, periodo = imputacion['detalle']
                detalle = id_detalle(adm, consorcio, periodo, unidad_funcional)

            resultado.append({
                'pago': id_pago(adm, consorcio, imputacion['pago']),
                'detalle_liquidacion': detalle,
                'concepto': imputacion['concepto'],
                'parte': imputacion['parte'],
                'monto': a_json(imputacion['monto']),
            })

        return resultado
