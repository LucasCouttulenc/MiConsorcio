from ..fixture import Fixture
from decouple import config
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from config.comun import GRUPO_ADMINISTRADORES, GRUPO_PROPIETARIOS
from django.contrib.auth import get_user_model
from faker import Faker
User = get_user_model()
faker = Faker()

class FixtureDeUser(Fixture):  
    def __init__(self):
        super().__init__(User)

    def campos(self):

        grupo_administradores = self.administrador.obtener_id_segun_campo(Group, 'name', GRUPO_ADMINISTRADORES)
        grupo_propietarios = self.administrador.obtener_id_segun_campo(Group, 'name', GRUPO_PROPIETARIOS)


        usuarios = [
            {
                'first_name': 'Super',
                'last_name': 'Usuario',
                'username': config('SUPERUSUARIO'),
                'password': make_password(config('CLAVE_SUPERUSUARIO')),
                'email': config('SUPERUSUARIO'),
                'is_superuser': True,
                'is_staff': True,
            },
            {
                'first_name': 'Paula',
                'last_name': 'Gonzalez (Administrador)',
                'username': config('ADMINISTRADOR'),
                'password': make_password(config('CLAVE_ADMINISTRADOR')),
                'email': config('ADMINISTRADOR'),
                'is_superuser': False,
                'is_staff': False,
                'groups': [grupo_administradores]
            },
            {
                'first_name': 'Pedro',
                'last_name': 'Sanchez (Propietario)',
                'username': config('PROPIETARIO'),
                'password': make_password(config('CLAVE_PROPIETARIO')),
                'email': config('PROPIETARIO'),
                'is_superuser': False,
                'is_staff': False,
                'groups': [grupo_propietarios]
            },
            {
                'first_name': 'Laura',
                'last_name': 'Lopez (Ambos)',
                'username': config('AMBOS'),
                'password': make_password(config('CLAVE_AMBOS')),
                'email': config('AMBOS'),
                'is_superuser': False,
                'is_staff': False,
                'groups': [grupo_administradores, grupo_propietarios]
            }
        ]

        propietarios = [
            {   
                'first_name': faker.first_name(),
                'last_name': faker.last_name(),
                'username': faker.email(),
                'password': make_password(f'clavepropietario{i}'),
                'email': faker.email(),
                'is_superuser': False,
                'is_staff': False,
                'groups': [grupo_propietarios]
            } for i in range(50)
        ]

        return usuarios + propietarios
    
        