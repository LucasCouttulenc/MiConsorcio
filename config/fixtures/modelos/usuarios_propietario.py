from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from ..fixture import Fixture
from config.comun import GRUPO_PROPIETARIOS
from usuarios.models import Propietario

User = get_user_model()


class FixtureDePropietario(Fixture):
    """Un propietario por cada usuario del grupo, aunque también esté en otros grupos."""

    def __init__(self):
        super().__init__(Propietario)

    def campos(self):
        grupo = self.administrador.obtener_id(Group, name=GRUPO_PROPIETARIOS)
        return [{'usuario': usuario} for usuario in self.administrador.obtener_ids(User, groups__contiene=grupo)]