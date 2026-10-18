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
        
        # Buscamos manualmente en el fixture de usuarios para ver quién tiene el grupo de propietario
        # (sin importar si tiene otros grupos también)
        fixture_user = self.administrador._diccionario_fixtures.get(User, [])
        
        usuarios = []
        for reg in fixture_user:
            grupos_del_usuario = reg['fields'].get('groups', [])
            if grupo_propietarios in grupos_del_usuario:
                usuarios.append(reg['pk'])

        return [
            {
                'usuario': usuario
            } for usuario in usuarios
        ]