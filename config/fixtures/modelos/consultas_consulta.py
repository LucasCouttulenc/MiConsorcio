import random
from datetime import timedelta

from django.utils import timezone

from ..fixture import Fixture
from consorcios.models import Consorcio, UnidadFuncional
from consultas.models import Consulta, EstadoConsulta
from usuarios.models import Administrador

# Cada plantilla es una conversación completa. Los mensajes son
# (horas desde que se creó la consulta, es de administración, texto).
# El estado es coherente con el hilo: una consulta abierta todavía no
# tiene respuesta; una en curso o cerrada, sí.
PLANTILLAS = [
    {
        'asunto': 'Filtración en el techo del baño',
        'estado': EstadoConsulta.EN_CURSO,
        'dias': 6,
        'mensajes': [
            (0, False, 'Buenas tardes. Desde hace unos días aparece una mancha de humedad en el techo del baño '
                       'y ayer empezó a gotear. Creo que viene del departamento de arriba.'),
            (20, True, 'Hola, gracias por avisar. Ya hablamos con el propietario de la unidad de arriba y el '
                       'plomero va a pasar el jueves por la mañana a revisar ambas unidades.'),
            (30, False, 'Perfecto, el jueves voy a estar en casa. Gracias.'),
        ],
    },
    {
        'asunto': 'Consulta por el aumento de las expensas',
        'estado': EstadoConsulta.CERRADA,
        'dias': 25,
        'mensajes': [
            (0, False, 'Hola, noté que las expensas de este mes subieron bastante respecto del anterior. '
                       '¿Me podrían explicar a qué se debe?'),
            (6, True, 'Hola. El aumento corresponde a la actualización salarial del encargado según el acuerdo '
                      'del SUTERH y al ajuste de la tarifa de luz de los espacios comunes. Lo podés ver '
                      'detallado en los rubros de la liquidación.'),
            (9, False, 'Entendido, muchas gracias por la aclaración.'),
        ],
    },
    {
        'asunto': 'Ruidos molestos en horario nocturno',
        'estado': EstadoConsulta.ABIERTA,
        'dias': 1,
        'mensajes': [
            (0, False, 'Quería reportar que en las últimas semanas hay ruidos fuertes pasada la medianoche, '
                       'casi todos los fines de semana. ¿Se puede recordar a los vecinos el reglamento interno?'),
        ],
    },
    {
        'asunto': 'Pedido de copia del reglamento de copropiedad',
        'estado': EstadoConsulta.CERRADA,
        'dias': 40,
        'mensajes': [
            (0, False, 'Buen día, ¿me podrían enviar una copia del reglamento de copropiedad? La necesito para '
                       'un trámite de escrituración.'),
            (4, True, 'Buen día. Te lo enviamos por correo electrónico. Cualquier otra cosa que necesites, avisanos.'),
        ],
    },
    {
        'asunto': 'El portero eléctrico no funciona',
        'estado': EstadoConsulta.EN_CURSO,
        'dias': 3,
        'mensajes': [
            (0, False, 'Hola, desde el lunes el portero eléctrico de mi unidad no suena cuando tocan el timbre.'),
            (5, True, 'Hola, gracias por avisar. Coordinamos con el técnico para esta semana. Te avisamos '
                      'el día y horario apenas lo confirme.'),
        ],
    },
    {
        'asunto': 'Solicitud de libre deuda',
        'estado': EstadoConsulta.ABIERTA,
        'dias': 0,
        'mensajes': [
            (0, False, 'Hola, estoy por vender la unidad y necesito el certificado de libre deuda de expensas. '
                       '¿Cuál es el procedimiento?'),
        ],
    },
]

PLANTILLAS_POR_ASUNTO = {plantilla['asunto']: plantilla for plantilla in PLANTILLAS}
CONSULTAS_POR_CONSORCIO = 3


def _fecha_creacion(plantilla, horas_desfase):
    ahora = timezone.now().replace(microsecond=0)
    return ahora - timedelta(days=plantilla['dias'], hours=horas_desfase)


class FixtureDeConsulta(Fixture):
    """Algunas consultas por consorcio, solo en consorcios que tienen un administrador que pueda responder."""

    dependencias_extra = (Administrador,)

    def __init__(self):
        super().__init__(Consulta)

    def campos(self):
        adm = self.administrador
        resultado = []

        for consorcio in adm.obtener_ids(Consorcio):
            if not adm.obtener_ids(Administrador, consorcios__contiene=consorcio):
                continue

            ufs_con_propietario = [
                uf for uf in adm.obtener_ids(UnidadFuncional, consorcio=consorcio)
                if adm.obtener_valor(UnidadFuncional, uf, 'propietario') is not None
            ]
            if not ufs_con_propietario:
                continue

            # La primera UF siempre entra, así los usuarios de prueba tienen consultas.
            cantidad = min(CONSULTAS_POR_CONSORCIO, len(ufs_con_propietario))
            ufs = [ufs_con_propietario[0]] + random.sample(ufs_con_propietario[1:], cantidad - 1)
            plantillas = random.sample(PLANTILLAS, cantidad)

            for uf, plantilla in zip(ufs, plantillas):
                # Unas horas de desfase para que no todas las consultas tengan la misma hora.
                creada = _fecha_creacion(plantilla, random.randint(0, 10))
                horas_ultimo_mensaje = plantilla['mensajes'][-1][0]
                resultado.append({
                    'unidad_funcional': uf,
                    'asunto': plantilla['asunto'],
                    'estado': plantilla['estado'],
                    # auto_now/auto_now_add no se aplican en loaddata: hay que cargarlos.
                    'creada': creada.isoformat(),
                    'actualizada': (creada + timedelta(hours=horas_ultimo_mensaje)).isoformat(),
                })

        return resultado