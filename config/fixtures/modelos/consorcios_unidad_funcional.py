from ..fixture import Fixture
from consorcios.models import UnidadFuncional, Consorcio
from usuarios.models import Propietario
import random

class FixtureDeUnidadFuncional(Fixture):
    def __init__(self):
        super().__init__(UnidadFuncional)
        
    def campos(self):

        propietarios = self.administrador.obtener_ids(Propietario)
        consorcios = self.administrador.obtener_ids(Consorcio)

        return [
            {
                'propietario': propietario,
                'consorcio': random.choice(consorcios)
            } for propietario in propietarios
        ]
        