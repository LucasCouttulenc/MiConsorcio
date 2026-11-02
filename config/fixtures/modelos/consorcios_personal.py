from datetime import date
from ..fixture import Fixture
from consorcios.models import Personal, Consorcio
from faker import Faker
faker = Faker("es_AR")


class FixtureDePersonal(Fixture):
    """Dos personas por consorcio: un encargado en relación de dependencia y limpieza tercerizada."""

    def __init__(self):
        super().__init__(Personal)

    def campos(self):
        resultado = []

        for consorcio in self.administrador.obtener_ids(Consorcio):
            # Nadie puede haber ingresado antes de que existiera el consorcio.
            fecha_creacion = date.fromisoformat(
                self.administrador.obtener_valor(Consorcio, consorcio, 'fecha_creacion')
            )

            for cargo, tipo, empresa in (
                ('Encargado', 'directo', ''),
                ('Personal de limpieza', 'tercerizado', faker.company()),
            ):
                resultado.append({
                    'consorcio': consorcio,
                    'nombre': faker.first_name(),
                    'apellido': faker.last_name(),
                    'dni': str(faker.random_int(min=20_000_000, max=45_000_000)),
                    'cargo': cargo,
                    'tipo_contratacion': tipo,
                    'empresa_tercerizada': empresa,
                    'telefono': faker.numerify(text='11########'),
                    'fecha_ingreso': str(faker.date_between(start_date=fecha_creacion, end_date='today')),
                })

        return resultado