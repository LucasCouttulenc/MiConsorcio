from decouple import config
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from ..fixture import Fixture
from config.comun import GRUPO_ADMINISTRADORES
from consorcios.models import Consorcio
from usuarios.models import Administrador

User = get_user_model()

# Qué consorcios (por posición) administra cada usuario de prueba. Se pisan en dos
# para tener consorcios con dos administradores, y entre los dos cubren todos.
CONSORCIOS_POR_ADMINISTRADOR = {
    'ADMINISTRADOR': slice(0, 6),  # Paula: consorcios 1 a 6
    'AMBOS': slice(4, 10),         # Laura: consorcios 5 a 10
}


class FixtureDeAdministrador(Fixture):
    def __init__(self):
        super().__init__(Administrador)

    def campos(self):
        adm = self.administrador
        grupo = adm.obtener_id(Group, name=GRUPO_ADMINISTRADORES)
        consorcios = adm.obtener_ids(Consorcio)
        asignados = {
            adm.obtener_id(User, username=config(clave)): consorcios[posiciones]
            for clave, posiciones in CONSORCIOS_POR_ADMINISTRADOR.items()
        }

        # Cualquier otro usuario del grupo queda como administrador sin consorcios.
        return [
            {'usuario': usuario, 'consorcios': asignados.get(usuario, [])}
            for usuario in adm.obtener_ids(User, groups__contiene=grupo)
        ]