from django.contrib.auth import get_user_model

from ..fixture import Fixture
from .obras_obra import TAREAS_POR_CONCEPTO
from .obras_proveedor import clave_responsable, id_proveedor
from obras.models import AsignacionProveedor, Obra
from usuarios.models import Administrador

User = get_user_model()


class FixtureDeAsignacionProveedor(Fixture):
    """
    Cada obra contrata proveedores de la cartera del administrador del consorcio,
    uno por rubro de la obra (así no se repite proveedor en la misma obra).
    """

    dependencias_extra = (Administrador, User)

    def __init__(self):
        super().__init__(AsignacionProveedor)

    def campos(self):
        adm = self.administrador
        resultado = []

        for obra in adm.obtener_ids(Obra):
            consorcio = adm.obtener_valor(Obra, obra, 'consorcio')
            clave = clave_responsable(adm, consorcio)
            for rubro, tarea in TAREAS_POR_CONCEPTO[adm.obtener_valor(Obra, obra, 'concepto')]:
                resultado.append({
                    'obra': obra,
                    'proveedor': id_proveedor(adm, clave, rubro),
                    'tarea': tarea,
                })

        return resultado