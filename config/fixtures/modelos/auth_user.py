from decouple import config
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from faker import Faker

from ..fixture import Fixture
from config.comun import GRUPO_ADMINISTRADORES, GRUPO_PROPIETARIOS

User = get_user_model()
faker = Faker('es_AR')

CANTIDAD_PROPIETARIOS = 50
# Todos los propietarios de prueba comparten clave: hashear 50 claves distintas hacía bastante más lento el iniciardb.
CLAVE_PROPIETARIOS = 'clavepropietario'


def email_propietario(numero):
    """Dominio example.com: nunca se manda un mail real a una dirección inventada."""
    return f'propietario{numero:02d}@example.com'


class FixtureDeUser(Fixture):
    def __init__(self):
        super().__init__(User)

    def campos(self):
        adm = self.administrador
        administradores = adm.obtener_id(Group, name=GRUPO_ADMINISTRADORES)
        propietarios = adm.obtener_id(Group, name=GRUPO_PROPIETARIOS)

        def usuario(nombre, apellido, clave_usuario, clave_password, grupos, superusuario=False):
            return {
                'first_name': nombre,
                'last_name': apellido,
                'username': config(clave_usuario),
                'email': config(clave_usuario),
                'password': make_password(config(clave_password)),
                'is_superuser': superusuario,
                'is_staff': superusuario,
                'groups': grupos,
            }

        usuarios = [
            usuario('Super', 'Usuario', 'SUPERUSUARIO', 'CLAVE_SUPERUSUARIO', [], superusuario=True),
            usuario('Paula', 'Gonzalez (Administrador)', 'ADMINISTRADOR', 'CLAVE_ADMINISTRADOR', [administradores]),
            usuario('Pedro', 'Sanchez (Propietario)', 'PROPIETARIO', 'CLAVE_PROPIETARIO', [propietarios]),
            usuario('Laura', 'Lopez (Ambos)', 'AMBOS', 'CLAVE_AMBOS', [administradores, propietarios]),
        ]

        clave = make_password(CLAVE_PROPIETARIOS)
        usuarios += [
            {
                'first_name': faker.first_name(),
                'last_name': faker.last_name(),
                'username': email_propietario(numero),
                'email': email_propietario(numero),
                'password': clave,
                'is_superuser': False,
                'is_staff': False,
                'groups': [propietarios],
            }
            for numero in range(1, CANTIDAD_PROPIETARIOS + 1)
        ]
        return usuarios