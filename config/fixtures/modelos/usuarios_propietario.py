
from ..fixture import Fixture
from usuarios.models import Propietario
from django.contrib.auth.models import Group
from config.comun import GRUPO_PROPIETARIOS
from django.contrib.auth import get_user_model
User = get_user_model()

class FixtureDePropietario(Fixture):
    def __init__(self):
        super().__init__(Propietario)

    def campos(self):
        grupo_propietarios = self.administrador.obtener_id_segun_campo(Group, 'name', GRUPO_PROPIETARIOS)
        usuarios = self.administrador.obtener_ids_segun_campo(User, 'groups', [grupo_propietarios])

        return [
            {
                'usuario': usuario
            } for usuario in usuarios
        ]
    