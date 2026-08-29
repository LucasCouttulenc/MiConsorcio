
from ..fixture import Fixture
from usuarios.models import Administrador
from django.contrib.auth.models import Group
from config.comun import GRUPO_ADMINISTRADORES
from django.contrib.auth import get_user_model
User = get_user_model()

class FixtureDeAdministrador(Fixture):
    def __init__(self):
        super().__init__(Administrador)

    def campos(self):
        grupo_administradores = self.administrador.obtener_id_segun_campo(Group, 'name', GRUPO_ADMINISTRADORES)
        usuarios = self.administrador.obtener_ids_segun_campo(User, 'groups', [grupo_administradores])

        return [
            {
                'usuario': usuario
            } for usuario in usuarios
        ]
    