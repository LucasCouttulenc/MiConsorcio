from .administrador_de_fixtures import AdministradorDeFixtures

CLAVE_MODELO = 'model'
CLAVE_PK = 'pk'
CLAVE_CAMPOS = 'fields'

class Fixture:
    def __init__(self, modelo):
        self.modelo = modelo
        self.registros = []
        self.administrador = AdministradorDeFixtures()

    def campos(self):
        raise NotImplementedError("El método 'campos' debe ser implementado en la subclase.")

    def a_dict(self):
        for campos in self.campos():
            self.registros.append({
                CLAVE_MODELO: self.modelo._meta.label_lower,
                CLAVE_PK: self._obtener_pk(),
                CLAVE_CAMPOS: campos                
            })
        return self.registros

    def _obtener_pk(self):
        return len(self.registros) + 1