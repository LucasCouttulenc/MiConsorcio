from datetime import date, timedelta

from ..fixture import Fixture
from .escenario_gastos import INICIO_OBRA_DIAS, OBRA_EXTRAORDINARIA
from consorcios.models import Consorcio
from obras.models import EstadoObra, Obra

# (concepto, estado, inicio y fin estimado en días respecto de hoy, descripción,
#  en qué consorcios va (según su índice), tareas: [(rubro del proveedor, tarea)])
OBRAS = [
    (
        OBRA_EXTRAORDINARIA, EstadoObra.EN_CURSO, -INICIO_OBRA_DIAS, 40,
        'Retiro de la membrana existente, reparación de carpeta y colocación de membrana '
        'geotextil con pintura reflectiva. Se financia con expensas extraordinarias en 3 cuotas.',
        lambda i: True,
        [('impermeabilizacion', 'Provisión y colocación de membrana'),
         ('electricidad', 'Reubicación de luminarias de terraza')],
    ),
    (
        'Pintura de palier y escaleras', EstadoObra.PLANIFICADA, 30, 75,
        'Lijado, enduido y pintura de paredes y barandas de palieres y escaleras de todos los pisos.',
        lambda i: True,
        [('pintura', 'Pintura de paredes y barandas')],
    ),
    (
        'Reparación de frente y balcones', EstadoObra.FINALIZADA, -240, -150,
        'Reparación de revoques flojos, tratamiento de hierros expuestos y pintura del frente.',
        lambda i: i % 2 == 0,
        [('fachada', 'Reparación de revoques y pintura de frente'),
         ('electricidad', 'Recambio de luminarias del frente')],
    ),
    (
        'Recambio de bomba de agua', EstadoObra.FINALIZADA, -90, -85,
        'Reemplazo de la bomba presurizadora por falla del motor.',
        lambda i: i % 2 == 1,
        [('plomeria', 'Provisión e instalación de bomba presurizadora')],
    ),
    (
        'Modernización del ascensor', EstadoObra.CANCELADA, 60, 150,
        'Se canceló en asamblea para priorizar la impermeabilización de la terraza.',
        lambda i: i % 3 == 0,
        [('ascensores', 'Cambio de botonera y puertas automáticas')],
    ),
]

TAREAS_POR_CONCEPTO = {concepto: tareas for concepto, *_, tareas in OBRAS}


class FixtureDeObra(Fixture):
    """
    En todos los consorcios: la impermeabilización en curso (la que se cobra en gastos)
    y una pintura planificada. Según el consorcio, además obras finalizadas o canceladas.
    """

    def __init__(self):
        super().__init__(Obra)

    def campos(self):
        hoy = date.today()
        return [
            {
                'consorcio': consorcio,
                'concepto': concepto,
                'descripcion': descripcion,
                'estado': estado,
                'fecha_inicio': str(hoy + timedelta(days=inicio)),
                'fecha_fin_estimada': str(hoy + timedelta(days=fin)),
            }
            for indice, consorcio in enumerate(self.administrador.obtener_ids(Consorcio))
            for concepto, estado, inicio, fin, descripcion, aplica, _ in OBRAS
            if aplica(indice)
        ]