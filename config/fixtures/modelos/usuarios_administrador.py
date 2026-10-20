
from ..fixture import Fixture
from usuarios.models import Administrador
from consorcios.models import Consorcio
from django.contrib.auth.models import Group
from config.comun import GRUPO_ADMINISTRADORES
from django.contrib.auth import get_user_model
import random
User = get_user_model()

class FixtureDeAdministrador(Fixture):
    def __init__(self):
        super().__init__(Administrador)

    def campos(self):
        grupo_administradores = self.administrador.obtener_id_segun_campo(Group, 'name', GRUPO_ADMINISTRADORES)
        # Un usuario puede pertenecer a más de un grupo (por ejemplo,
        # administrador y propietario). Comparar la lista completa de grupos
        # dejaba afuera a esos usuarios.
        usuarios = [
            registro['pk']
            for registro in self.administrador._diccionario_fixtures.get(User, [])
            if grupo_administradores in registro['fields'].get('groups', [])
        ]
        consorcios = self.administrador.obtener_ids(Consorcio)

        return [
            {
                'usuario': usuario,
                'consorcios': consorcios[:random.randint(1, 5)]  # Asignar un número aleatorio de consorcios al administrador
            } for usuario in usuarios
        ]

