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

        resultado = []

        # 5 unidadades funcionales por cada consorcio. 
        # Cada propitario tiene una sola unidad funcional en total.
        # No se repiten departamentos dentro de un mismo consorcio.
        for consorcio_id in consorcios:
            for piso in range(1, 6):
                departamento = "A"
                propietario = propietarios.pop(0)
                resultado.append({
                    'propietario_id': propietario,
                    'consorcio_id': consorcio_id,
                    'piso': piso,
                    'departamento': departamento
                })

        return resultado
        
        
            

        