from ..fixture import Fixture
from consorcios.models import Consorcio
from contactos.models import ContactoAdministracion

# Dos administraciones que se reparten los consorcios. La segunda no tiene
# sitio web, para probar un contacto con datos parciales.
ADMINISTRACIONES = [
    {
        'nombre': 'Administración Gonzalez & Asoc.',
        'direccion': 'Av. Corrientes 1250, piso 4, of. B',
        'localidad': 'CABA',
        'telefono': '1143215678',
        'horario': 'Lunes a viernes de 10 a 17 hs',
        'email': 'contacto@admgonzalez.com.ar',
        'sitio_web': 'https://www.admgonzalez.com.ar',
    },
    {
        'nombre': 'López Propiedades',
        'direccion': 'Av. Cabildo 1890, piso 2',
        'localidad': 'CABA',
        'telefono': '1147893456',
        'horario': 'Lunes a viernes de 9 a 16 hs',
        'email': 'info@lopezpropiedades.com.ar',
        'sitio_web': '',
    },
]


class FixtureDeContactoAdministracion(Fixture):
    """
    Un contacto por consorcio (es OneToOne). El último consorcio queda con
    el contacto vacío para probar el caso esta_vacio.
    """

    def __init__(self):
        super().__init__(ContactoAdministracion)

    def campos(self):
        consorcios = self.administrador.obtener_ids(Consorcio)
        resultado = []

        for indice, consorcio in enumerate(consorcios):
            if consorcio == consorcios[-1]:
                resultado.append({'consorcio': consorcio})
                continue

            resultado.append({
                'consorcio': consorcio,
                **ADMINISTRACIONES[indice % len(ADMINISTRACIONES)],
            })

        return resultado