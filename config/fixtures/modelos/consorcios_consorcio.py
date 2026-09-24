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
                'direccion': faker.address(), 
            } for _ in range(15)
        ]