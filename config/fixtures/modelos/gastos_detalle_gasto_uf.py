from ..fixture import Fixture
from .escenario_gastos import DEPENDENCIAS_ESCENARIO, a_json, id_liquidacion, obtener_escenario
from gastos.models import DetalleGastoUF, Gasto, Liquidacion


class FixtureDeDetalleGastoUf(Fixture):
    """Cómo se repartió cada gasto entre las UF que lo pagan (general, parcial o particular)."""

    dependencias_extra = DEPENDENCIAS_ESCENARIO + (Liquidacion,)

    def __init__(self):
        super().__init__(DetalleGastoUF)

    def campos(self):
        adm = self.administrador
        escenario = obtener_escenario(adm)
        ids_gastos = {}  # Son miles de filas: cada gasto se busca una sola vez.

        def id_gasto(consorcio, periodo, posicion):
            clave = (consorcio, periodo, posicion)
            if clave not in ids_gastos:
                ids_gastos[clave] = adm.obtener_id(
                    Gasto, liquidacion=id_liquidacion(adm, consorcio, periodo), posicion=posicion,
                )
            return ids_gastos[clave]

        return [
            {
                'gasto': id_gasto(d['consorcio'], d['periodo'], d['posicion']),
                'unidad_funcional': d['unidad_funcional'],
                'porcentaje_aplicado': a_json(d['porcentaje_aplicado']),
                'monto_asignado': a_json(d['monto_asignado']),
            }
            for d in escenario.distribuciones
        ]
