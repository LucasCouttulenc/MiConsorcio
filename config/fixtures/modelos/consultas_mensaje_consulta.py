from datetime import datetime, timedelta

from ..fixture import Fixture
from .consultas_consulta import PLANTILLAS_POR_ASUNTO
from consorcios.models import UnidadFuncional
from consultas.models import Consulta, MensajeConsulta
from usuarios.models import Administrador, Propietario


class FixtureDeMensajeConsulta(Fixture):
    """
    Arma el hilo de cada consulta a partir de su plantilla. Los mensajes del
    propietario los firma el usuario dueño de la UF; los de administración,
    un administrador asignado al consorcio.
    """

    dependencias_extra = (Administrador, Propietario)

    def __init__(self):
        super().__init__(MensajeConsulta)

    def campos(self):
        adm = self.administrador
        resultado = []

        for consulta in adm.obtener_ids(Consulta):
            uf = adm.obtener_valor(Consulta, consulta, 'unidad_funcional')
            consorcio = adm.obtener_valor(UnidadFuncional, uf, 'consorcio')
            propietario = adm.obtener_valor(UnidadFuncional, uf, 'propietario')

            usuario_propietario = adm.obtener_valor(Propietario, propietario, 'usuario')
            administrador = adm.obtener_ids(Administrador, consorcios__contiene=consorcio)[0]
            usuario_administracion = adm.obtener_valor(Administrador, administrador, 'usuario')

            creada = datetime.fromisoformat(adm.obtener_valor(Consulta, consulta, 'creada'))
            plantilla = PLANTILLAS_POR_ASUNTO[adm.obtener_valor(Consulta, consulta, 'asunto')]

            for horas, de_administracion, texto in plantilla['mensajes']:
                resultado.append({
                    'consulta': consulta,
                    'autor': usuario_administracion if de_administracion else usuario_propietario,
                    'de_administracion': de_administracion,
                    'texto': texto,
                    'creado': (creada + timedelta(hours=horas)).isoformat(),
                })

        return resultado