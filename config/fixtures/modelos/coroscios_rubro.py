from ..fixture import Fixture
from consorcios.models import Rubro, Consorcio


class FixtureDeRubro(Fixture):
    def __init__(self):
        super().__init__(Rubro)

    def campos(self):
        consorcios = self.administrador.obtener_ids(Consorcio)

        rubros_base = [
            'REMUNERACIONES AL PERSONAL',
            'SERVICIOS PÚBLICOS',
            'MANTENIMIENTO DE PARTES COMUNES',
            'GASTOS DE ADMINISTRACIÓN',
        ]

        resultado = []
        for consorcio_id in consorcios:
            for nombre in rubros_base:
                resultado.append({
                    'consorcio_id': consorcio_id,
                    'nombre': nombre,
                })
        return resultado