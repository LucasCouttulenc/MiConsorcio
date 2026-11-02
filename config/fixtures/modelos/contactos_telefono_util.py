from ..fixture import Fixture
from consorcios.models import Consorcio, Personal
from contactos.models import TelefonoUtil
from obras.models import Proveedor
from faker import Faker
faker = Faker("es_AR")

EMERGENCIAS = [
    ('Emergencias', '911', 'Policía y emergencias generales'),
    ('Bomberos', '100', ''),
    ('SAME', '107', 'Emergencias médicas'),
]

PROVEEDOR_ASCENSORES = 'Ascensores Delta'


class FixtureDeTelefonoUtil(Fixture):
    """
    Por consorcio: el encargado (tomado del fixture de Personal), el service de
    ascensores (tomado del fixture de Proveedor), una cerrajería y las emergencias.
    """

    dependencias_extra = (Personal, Proveedor)

    def __init__(self):
        super().__init__(TelefonoUtil)

    def campos(self):
        adm = self.administrador
        ascensores = adm.obtener_id(Proveedor, nombre=PROVEEDOR_ASCENSORES)
        telefono_ascensores = adm.obtener_valor(Proveedor, ascensores, 'telefono')

        resultado = []
        for consorcio in adm.obtener_ids(Consorcio):
            telefonos = []

            for encargado in adm.obtener_ids(Personal, consorcio=consorcio, cargo='Encargado'):
                nombre = adm.obtener_valor(Personal, encargado, 'nombre')
                apellido = adm.obtener_valor(Personal, encargado, 'apellido')
                telefonos.append((
                    'Encargado',
                    adm.obtener_valor(Personal, encargado, 'telefono'),
                    f'{nombre} {apellido}, lunes a viernes de 7 a 15 hs',
                ))

            telefonos.append((
                'Ascensores',
                telefono_ascensores,
                f'{PROVEEDOR_ASCENSORES}, guardia 24 hs. Indicar dirección y número de ascensor.',
            ))
            telefonos.append((
                'Cerrajería',
                faker.numerify(text='11########'),
                f'Cerrajería {faker.last_name()}, urgencias 24 hs',
            ))
            telefonos.extend(EMERGENCIAS)

            resultado.extend(
                {'consorcio': consorcio, 'nombre': nombre, 'telefono': telefono, 'detalle': detalle}
                for nombre, telefono, detalle in telefonos
            )

        return resultado