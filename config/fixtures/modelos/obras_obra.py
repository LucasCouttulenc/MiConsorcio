from datetime import date, timedelta
from ..fixture import Fixture
from consorcios.models import Consorcio
from obras.models import EstadoObra, Obra

OBRAS = [
    ('Impermeabilización de terraza', EstadoObra.EN_CURSO, -20, 40),
    ('Pintura de palier y escaleras', EstadoObra.PLANIFICADA, 30, 75),
]


class FixtureDeObra(Fixture):
    def __init__(self):
        super().__init__(Obra)

    def campos(self):
        hoy = date.today()
        return [
            {
                'consorcio': consorcio,
                'concepto': concepto,
                'estado': estado,
                'fecha_inicio': str(hoy + timedelta(days=inicio)),
                'fecha_fin_estimada': str(hoy + timedelta(days=fin)),
            }
            for consorcio in self.administrador.obtener_ids(Consorcio)
            for concepto, estado, inicio, fin in OBRAS
        ]
