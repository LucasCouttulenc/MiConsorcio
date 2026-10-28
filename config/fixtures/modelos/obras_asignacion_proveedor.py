from ..fixture import Fixture
from obras.models import AsignacionProveedor, Obra, Proveedor

# Por concepto de obra: (índice del proveedor en el fixture, tarea)
TAREAS = {
    'Impermeabilización de terraza': [(0, 'Provisión y colocación de membrana'), (3, 'Reubicación de luminarias de terraza')],
    'Pintura de palier y escaleras': [(2, 'Pintura de paredes y barandas')],
}


class FixtureDeAsignacionProveedor(Fixture):
    def __init__(self):
        super().__init__(AsignacionProveedor)

    def campos(self):
        proveedores = self.administrador.obtener_ids(Proveedor)
        obras = self.administrador._diccionario_fixtures[Obra]
        return [
            {'obra': obra['pk'], 'proveedor': proveedores[indice], 'tarea': tarea}
            for obra in obras
            for indice, tarea in TAREAS[obra['fields']['concepto']]
        ]
