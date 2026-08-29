from config.comun import *
from ..fixture import Fixture
from django.contrib.auth.models import Group


class FixtureDeGroup(Fixture):
    def __init__(self):
        super().__init__(Group)
        
    def campos(self):
        return [
            {
                'name': GRUPO_ADMINISTRADORES
            },
            {
                'name': GRUPO_PROPIETARIOS
            },
        ]