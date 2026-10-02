from django.contrib.auth.models import Group, Permission
from config.comun import (
    GRUPO_ADMINISTRADORES,
    GRUPO_PROPIETARIOS,
    PERMISOS_ADMINISTRADORES,
    PERMISOS_PROPIETARIOS,
)
from ..fixture import Fixture


class FixtureDeGroup(Fixture):
    def __init__(self):
        super().__init__(Group)

    def campos(self):
        return [
            {
                'name': GRUPO_ADMINISTRADORES,
                'permissions': self._ids_permisos(PERMISOS_ADMINISTRADORES),
            },
            {
                'name': GRUPO_PROPIETARIOS,
                'permissions': self._ids_permisos(PERMISOS_PROPIETARIOS),
            },
        ]

    def _ids_permisos(self, lista_codenames):
        """
        Traduce una lista de codenames ('view_consorcio') a IDs de Permission.
        Busca en todas las apps por codename.
        """
        ids = []
        for codename in lista_codenames:
            try:
                p = Permission.objects.get(codename=codename)
                ids.append(p.pk)
            except Permission.DoesNotExist:
                print(f"  Permiso no encontrado: {codename}")
            except Permission.MultipleObjectsReturned:
                print(f"  Permiso ambiguo (existe en varias apps): {codename}")
        return ids