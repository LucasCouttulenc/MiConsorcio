import random
from decimal import Decimal
from itertools import cycle

from ..fixture import Fixture
from consorcios.models import UnidadFuncional, Consorcio
from usuarios.models import Propietario

PESO_DEPARTAMENTO = {'A': Decimal('1.2'), 'B': Decimal('0.8')}
CENTESIMO_DE_PUNTO = Decimal('0.0001')


def _alicuotas(departamentos):
    """Reparte el 100% según el peso de cada departamento. La última UF absorbe el redondeo."""
    peso_total = sum(PESO_DEPARTAMENTO[d] for d in departamentos)
    alicuotas = [
        (PESO_DEPARTAMENTO[d] * 100 / peso_total).quantize(CENTESIMO_DE_PUNTO)
        for d in departamentos
    ]
    alicuotas[-1] += Decimal('100') - sum(alicuotas)
    return alicuotas


class FixtureDeUnidadFuncional(Fixture):
    def __init__(self):
        super().__init__(UnidadFuncional)

    def campos(self):
        propietarios = self.administrador.obtener_ids(Propietario)
        # Si hay más UF que propietarios, algunos propietarios tienen más de una UF.
        siguiente_propietario = cycle(propietarios) if propietarios else cycle([None])

        resultado = []
        for consorcio in self.administrador.obtener_ids(Consorcio):
            cantidad_pisos = random.randint(3, 5)
            unidades = [(piso, depto) for piso in range(1, cantidad_pisos + 1) for depto in PESO_DEPARTAMENTO]
            alicuotas = _alicuotas([depto for _, depto in unidades])

            for numero, ((piso, departamento), alicuota) in enumerate(zip(unidades, alicuotas), start=1):
                # La última UF de cada consorcio queda pendiente de propietario (ver invitaciones).
                sin_propietario = numero == len(unidades)
                resultado.append({
                    'propietario': None if sin_propietario else next(siguiente_propietario),
                    'consorcio': consorcio,
                    'piso': piso,
                    'departamento': departamento,
                    'alicuota': str(alicuota),
                })

        return resultado