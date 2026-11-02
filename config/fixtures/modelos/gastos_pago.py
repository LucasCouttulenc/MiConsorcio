from ..fixture import Fixture
from .escenario_gastos import DEPENDENCIAS_ESCENARIO, a_json, id_detalle, obtener_escenario
from gastos.models import Pago

CAMPOS = ('fecha_pago', 'monto_pagado', 'medio_pago', 'estado', 'fecha_registro', 'notas_admin')


class FixtureDePago(Fixture):
    """Pagos validados, pendientes de validación y rechazados."""

    dependencias_extra = DEPENDENCIAS_ESCENARIO

    def __init__(self):
        super().__init__(Pago)

    def campos(self):
        adm = self.administrador
        escenario = obtener_escenario(adm)
        return [
            {
                'detalle_liquidacion': id_detalle(adm, pago['consorcio'], pago['periodo'], pago['unidad_funcional']),
                'comprobante': '',
                **{campo: a_json(pago[campo]) for campo in CAMPOS},
            }
            for pago in escenario.pagos
        ]
