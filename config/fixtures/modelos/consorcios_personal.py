from ..fixture import Fixture
from consorcios.models import Personal, Consorcio
from faker import Faker
faker = Faker("es_AR")

CARGOS = ["Encargado", "Portero", "Personal de limpieza", "Ayudante"]

class FixtureDePersonal(Fixture):
    def __init__(self):
        super().__init__(Personal)

    def campos(self):
        consorcios = self.administrador.obtener_ids(Consorcio)

        resultado = []

        # 2 personas por consorcio: una en relación de dependencia y una tercerizada.
        for consorcio_id in consorcios:
            resultado.append({
                'consorcio_id': consorcio_id,
                'nombre': faker.first_name(),
                'apellido': faker.last_name(),
                'dni': faker.numerify(text='########'),
                'cargo': CARGOS[0],
                'tipo_contratacion': 'directo',
                'empresa_tercerizada': '',
                'telefono': faker.numerify(text='11########'),
                'fecha_ingreso': str(faker.date_between(start_date='-5y', end_date='today')),
            })
            resultado.append({
                'consorcio_id': consorcio_id,
                'nombre': faker.first_name(),
                'apellido': faker.last_name(),
                'dni': faker.numerify(text='########'),
                'cargo': CARGOS[2],
                'tipo_contratacion': 'tercerizado',
                'empresa_tercerizada': faker.company(),
                'telefono': faker.numerify(text='11########'),
                'fecha_ingreso': str(faker.date_between(start_date='-5y', end_date='today')),
            })

        return resultado
