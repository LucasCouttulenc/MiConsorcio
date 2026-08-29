from ..fixture import Fixture
from decouple import config
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from config.comun import GRUPO_ADMINISTRADORES, GRUPO_PROPIETARIOS
from django.contrib.auth import get_user_model
User = get_user_model()

class FixtureDeUser(Fixture):  
    def __init__(self):
        super().__init__(User)

    def campos(self):

        grupo_administradores = self.administrador.obtener_id_segun_campo(Group, 'name', GRUPO_ADMINISTRADORES)
        grupo_propietarios = self.administrador.obtener_id_segun_campo(Group, 'name', GRUPO_PROPIETARIOS)

        return [
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
                'first_name': 'Administrador',
                'last_name': 'de Consorcios',
                'username': config('ADMINISTRADOR'),
                'password': make_password(config('CLAVE_ADMINISTRADOR')),
                'email': config('ADMINISTRADOR'),
                'is_superuser': False,
                'is_staff': False,
                'groups': [grupo_administradores]
            },
            {
                'first_name': 'Propietario',
                'last_name': 'de Unidad',
                'username': config('PROPIETARIO'),
                'password': make_password(config('CLAVE_PROPIETARIO')),
                'email': config('PROPIETARIO'),
                'is_superuser': False,
                'is_staff': False,
                'groups': [grupo_propietarios]
            },
            {
                'first_name': 'Ambos',
                'last_name': 'Roles',
                'username': config('AMBOS'),
                'password': make_password(config('CLAVE_AMBOS')),
                'email': config('AMBOS'),
                'is_superuser': False,
                'is_staff': False,
                'groups': [grupo_administradores, grupo_propietarios]
            }
        ]
    
        