from decouple import config
from django.contrib.auth import get_user_model
from ..fixture import Fixture
from obras.models import Proveedor
User = get_user_model()

PROVEEDORES = [
    ('Impermeabilizaciones Sur', 'Impermeabilizaciones Sur S.R.L.', '1145671234', 'contacto@impersur.com.ar'),
    ('Ascensores Delta', 'Delta Elevadores S.A.', '1148902211', 'servicio@ascensoresdelta.com.ar'),
    ('Pinturas Gómez', 'Gómez Juan Carlos', '1156783344', 'pinturasgomez@gmail.com'),
    ('Electricidad Norte', 'Norte Instalaciones S.R.L.', '1133457788', 'obras@electricidadnorte.com.ar'),
]


class FixtureDeProveedor(Fixture):
    def __init__(self):
        super().__init__(Proveedor)

    def campos(self):
        administrador = self.administrador.obtener_id_segun_campo(User, 'username', config('ADMINISTRADOR'))
        return [
            {'creado_por': administrador, 'nombre': nombre, 'razon_social': razon_social, 'telefono': telefono, 'email': email}
            for nombre, razon_social, telefono, email in PROVEEDORES
        ]
