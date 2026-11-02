import re

from django.contrib.auth import get_user_model

from ..fixture import Fixture
from .escenario_gastos import DEPENDENCIAS_ESCENARIO, a_json, obtener_escenario
from contactos.models import ContactoAdministracion
from gastos.models import Liquidacion
from usuarios.models import Administrador

User = get_user_model()

# Datos fiscales de las administraciones del fixture de contactos (por nombre).
DATOS_FISCALES = {
    'Administración Gonzalez & Asoc.': {
        'admin_fiscal': 'Responsable Inscripto', 'admin_cuit': '30715553348', 'admin_rpa': '1234',
    },
    'López Propiedades': {
        'admin_fiscal': 'Monotributo', 'admin_cuit': '27284561231', 'admin_rpa': '2871',
    },
}


class FixtureDeLiquidacion(Fixture):
    """
    Liquidaciones cerradas de los últimos meses, con totales que coinciden con sus gastos.
    En datos_borrador guardan los datos de la administración que imprime el PDF.
    """

    dependencias_extra = DEPENDENCIAS_ESCENARIO + (ContactoAdministracion, Administrador, User)

    def __init__(self):
        super().__init__(Liquidacion)

    def campos(self):
        escenario = obtener_escenario(self.administrador)
        administraciones = {}

        resultado = []
        for liquidacion in escenario.liquidaciones:
            consorcio = liquidacion['consorcio']
            if consorcio not in administraciones:
                administraciones[consorcio] = self._datos_administracion(consorcio)
            resultado.append({
                **{campo: a_json(valor) for campo, valor in liquidacion.items()},
                'cerrada': True,
                'datos_borrador': {'administracion': administraciones[consorcio]},
            })
        return resultado

    def _datos_administracion(self, consorcio):
        adm = self.administrador
        contacto = adm.obtener_id(ContactoAdministracion, consorcio=consorcio)
        razon = adm.obtener_valor(ContactoAdministracion, contacto, 'nombre') or ''

        nombre = ''
        administradores = adm.obtener_ids(Administrador, consorcios__contiene=consorcio)
        if administradores:
            usuario = adm.obtener_valor(Administrador, administradores[0], 'usuario')
            apellido = re.sub(r'\s*\(.*\)$', '', adm.obtener_valor(User, usuario, 'last_name'))
            nombre = f"{adm.obtener_valor(User, usuario, 'first_name')} {apellido}"

        return {
            'admin_razon': razon,
            'admin_nombre': nombre,
            'admin_domicilio': adm.obtener_valor(ContactoAdministracion, contacto, 'direccion') or '',
            'admin_telefono': adm.obtener_valor(ContactoAdministracion, contacto, 'telefono') or '',
            'admin_mail': adm.obtener_valor(ContactoAdministracion, contacto, 'email') or '',
            **DATOS_FISCALES.get(razon, {'admin_fiscal': '', 'admin_cuit': '', 'admin_rpa': ''}),
        }
