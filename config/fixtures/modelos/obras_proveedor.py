from decouple import config
from django.contrib.auth import get_user_model

from ..fixture import Fixture
from obras.models import Proveedor
from usuarios.models import Administrador

User = get_user_model()

# Cada administrador tiene su propia cartera de proveedores (creado_por).
# Clave: variable de entorno con el usuario. Valor: {rubro: (nombre, razón social, teléfono, mail)}.
# 'Ascensores Delta' tiene que existir una sola vez: lo usan TelefonoUtil y los servicios recurrentes.
PROVEEDORES = {
    'ADMINISTRADOR': {
        'impermeabilizacion': ('Impermeabilizaciones Sur', 'Impermeabilizaciones Sur S.R.L.', '1145671234', 'contacto@impersur.com.ar'),
        'ascensores': ('Ascensores Delta', 'Delta Elevadores S.A.', '1148902211', 'servicio@ascensoresdelta.com.ar'),
        'pintura': ('Pinturas Gómez', 'Gómez Juan Carlos', '1156783344', 'pinturasgomez@gmail.com'),
        'electricidad': ('Electricidad Norte', 'Norte Instalaciones S.R.L.', '1133457788', 'obras@electricidadnorte.com.ar'),
        'fachada': ('Frentes Porteños', 'Frentes Porteños S.A.', '1147761290', 'presupuestos@frentesportenos.com.ar'),
        'plomeria': ('Bombas y Tanques', 'Bombas y Tanques S.R.L.', '1152348876', 'guardia@bombasytanques.com.ar'),
    },
    'AMBOS': {
        'impermeabilizacion': ('Techos del Oeste', 'Techos del Oeste S.R.L.', '1146512290', 'info@techosdeloeste.com.ar'),
        'ascensores': ('Elevadores Belgrano', 'Elevadores Belgrano S.A.', '1147843310', 'service@elevadoresbelgrano.com.ar'),
        'pintura': ('Pinturería Ramírez', 'Ramírez Hugo Daniel', '1161227845', 'ramirezpinturas@gmail.com'),
        'electricidad': ('Electro Service BA', 'Electro Service BA S.R.L.', '1139087766', 'contacto@electroserviceba.com.ar'),
        'fachada': ('Restauraciones Palermo', 'Restauraciones Palermo S.A.', '1148335521', 'obras@restpalermo.com.ar'),
        'plomeria': ('Plomería Integral Rossi', 'Rossi Marcelo Alejandro', '1158890012', 'plomeriarossi@gmail.com'),
    },
}
ADMINISTRADOR_POR_DEFECTO = 'ADMINISTRADOR'


def usuario_de(adm, clave):
    return adm.obtener_id(User, username=config(clave))


def clave_responsable(adm, consorcio):
    """
    Administrador que contrata las obras del consorcio: el primero asignado a él.
    Si no tiene ninguno de los que tienen cartera de proveedores, el administrador por defecto.
    """
    usuarios = {usuario_de(adm, clave): clave for clave in PROVEEDORES}
    for administrador in adm.obtener_ids(Administrador, consorcios__contiene=consorcio):
        clave = usuarios.get(adm.obtener_valor(Administrador, administrador, 'usuario'))
        if clave:
            return clave
    return ADMINISTRADOR_POR_DEFECTO


def id_proveedor(adm, clave, rubro):
    nombre = PROVEEDORES[clave][rubro][0]
    return adm.obtener_id(Proveedor, creado_por=usuario_de(adm, clave), nombre=nombre)


class FixtureDeProveedor(Fixture):
    def __init__(self):
        super().__init__(Proveedor)

    def campos(self):
        return [
            {
                'creado_por': usuario_de(self.administrador, clave),
                'nombre': nombre,
                'razon_social': razon_social,
                'telefono': telefono,
                'email': email,
            }
            for clave, proveedores in PROVEEDORES.items()
            for nombre, razon_social, telefono, email in proveedores.values()
        ]