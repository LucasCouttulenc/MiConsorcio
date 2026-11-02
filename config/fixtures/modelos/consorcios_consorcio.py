import random

from ..fixture import Fixture
from consorcios.models import Consorcio
from faker import Faker
faker = Faker("es_AR")

# (calle, altura, código postal, barrio)
DIRECCIONES = [
    ('Av. Rivadavia', 5240, 1424, 'Caballito'),
    ('Av. Santa Fe', 3155, 1425, 'Palermo'),
    ('Av. Cabildo', 2150, 1428, 'Belgrano'),
    ('Gurruchaga', 870, 1414, 'Villa Crespo'),
    ('Av. Corrientes', 4380, 1195, 'Almagro'),
    ('Juncal', 2460, 1125, 'Recoleta'),
    ('Defensa', 1120, 1065, 'San Telmo'),
    ('Av. Triunvirato', 4535, 1431, 'Villa Urquiza'),
    ('Av. del Libertador', 7340, 1429, 'Núñez'),
    ('Av. Nazca', 1580, 1416, 'Flores'),
]

HORARIOS = [
    'Lunes a viernes de 9 a 13 hs',
    'Lunes a viernes de 10 a 17 hs',
    'Martes y jueves de 14 a 18 hs',
]

TASAS_INTERES = ['2.50', '3.00', '3.50', '4.00']
PORCENTAJES_FONDO_RESERVA = ['0.00', '5.00', '10.00']

PESOS_CUIT = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]


def _generar_cuit(usados):
    """CUIT de persona jurídica (prefijo 30) con dígito verificador válido."""
    while True:
        base = '30' + faker.numerify(text='########')
        resto = sum(int(d) * p for d, p in zip(base, PESOS_CUIT)) % 11
        verificador = 0 if resto == 0 else 11 - resto
        if verificador == 10:
            continue
        cuit = f'{base}{verificador}'
        if cuit not in usados:
            usados.add(cuit)
            return cuit


class FixtureDeConsorcio(Fixture):
    def __init__(self):
        super().__init__(Consorcio)

    def campos(self):
        cuits = set()
        return [
            {
                'nombre': f'Consorcio {calle} {altura}',
                'cuit': _generar_cuit(cuits),
                'clave_suterh': faker.unique.numerify(text='######'),
                'fecha_creacion': str(faker.date_between(start_date='-40y', end_date='-1y')),
                'calle': calle,
                'altura': altura,
                'codigo_postal': codigo_postal,
                'localidad': f'{barrio}, CABA',
                'horario_atencion': random.choice(HORARIOS),
                'tasa_interes_mensual': random.choice(TASAS_INTERES),
                'fondo_reserva_nombre': 'Fondo de reserva',
                'fondo_reserva_porcentaje': random.choice(PORCENTAJES_FONDO_RESERVA),
            }
            for calle, altura, codigo_postal, barrio in DIRECCIONES
        ]