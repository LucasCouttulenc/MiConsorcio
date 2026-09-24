from datetime import datetime, timedelta

from ..fixture import Fixture
from consorcios.models import Consorcio
from usuarios.models import Administrador
from faker import Faker
faker = Faker("es_AR")

class FixtureDeConsorcio(Fixture):
    def __init__(self):
        super().__init__(Consorcio)
        
    def campos(self):

        return [
            {
                'nombre': faker.company(),
                'cuit': faker.numerify(text='30#########'),
                'clave_suterh': faker.password(length=10, special_chars=False),
                'fecha_creacion': str(datetime.now().date() - timedelta(days=faker.random_int(min=0, max=3650))),
                'calle': faker.street_name(),
                'altura': faker.building_number(),
                'codigo_postal': faker.numerify(text='#####'),
            } for _ in range(15)
        ]