import importlib
import json
import networkx as nx
from pathlib import Path

CLAVE_MODELO = 'model'
CLAVE_PK = 'pk'
CLAVE_CAMPOS = 'fields'

class AdministradorDeFixtures:
    _instacia = None

    def __new__(cls, *args, carpeta=None, **kwargs):
        if cls._instacia is None:
            cls._instacia = super().__new__(cls, *args, **kwargs)
            cls._instacia._inicializar()
            if carpeta is None:
                raise ValueError("La carpeta de modelos no puede ser None")
            cls._instacia.carpeta = carpeta
        return cls._instacia

    def _inicializar(self):
        self._diccionario_fixtures = {}
        self._fixtures = {}

    def agregar(self, fixture):
        self._fixtures[fixture.modelo] = fixture

    def obtener_id_segun_campo(self, modelo, campo, valor):
        nombre_modelo = modelo._meta.label_lower
        fixture = self._diccionario_fixtures.get(modelo)

        if not fixture:
            raise Exception(f"No se encontro un fixture para el modelo {nombre_modelo}")

        for registro in fixture:
            if registro[CLAVE_CAMPOS].get(campo) == valor:
                return registro[CLAVE_PK]

        raise Exception(f"No se encontro un fixture para el modelo {nombre_modelo} con {campo}={valor}")

    def obtener_ids(self, modelo):
        nombre_modelo = modelo._meta.label_lower
        fixture = self._diccionario_fixtures.get(modelo)

        if not fixture:
            raise Exception(f"No se encontro fixture para el modelo {nombre_modelo}")

        return [registro[CLAVE_PK] for registro in fixture]

    def obtener_ids_segun_campo(self, modelo, campo, valor):
        nombre_modelo = modelo._meta.label_lower
        fixture = self._diccionario_fixtures.get(modelo)

        if not fixture:
            raise Exception(f"No se encontro fixture para el modelo {nombre_modelo}")

        return [registro[CLAVE_PK] for registro in fixture if registro[CLAVE_CAMPOS].get(campo) == valor]

    def exportar_a_archivo(self, nombre_archivo):
        # Importar todos los archivos de fixtures
        archivos_de_fixtures = Path(f'config/fixtures/{self.carpeta}').rglob('*.py')

        for archivo in archivos_de_fixtures:
            if archivo.stem == '__init__': continue

            # Importar módulo y obtener clase de fixture
            modulo = importlib.import_module(f"config.fixtures.{self.carpeta}.{archivo.stem}")
            nombre_modelo = ''.join([palabra.capitalize() for palabra in archivo.stem.split('_')[1:]])
            try:
                clase_fixture = getattr(modulo, f"FixtureDe{nombre_modelo}")
            except AttributeError:
                print(f"Advertencia: No se encontró la clase FixtureDe{nombre_modelo} en {archivo.stem}. Asegúrate de que el nombre de la clase coincida con el nombre del modelo.")
                continue
                
            # Agregar fixture
            self.agregar(clase_fixture())

        # Ordenar topologicamente
        modelos_ordenados = self._ordenar_modelos_topologicamente()

        # Guardar fixtures en diccionario
        for modelo in modelos_ordenados:
            if modelo not in self._fixtures: continue

            self._diccionario_fixtures[modelo] = self._fixtures[modelo].a_dict()

        # Escrbir fixtures en archivo
        lista_fixtures = []
        for fixture in self._diccionario_fixtures.values():
            lista_fixtures.extend(fixture)

        with open(nombre_archivo, 'w') as f:
            f.write(json.dumps(lista_fixtures, indent=4))

    def _ordenar_modelos_topologicamente(self):
        modelos = self._fixtures.keys()
        grafo = nx.DiGraph()

        # Crear grafo con modelos como nodos y dependencias como aristas
        for modelo in modelos:
            dependencias = self._obtener_dependecias(modelo)
            if not dependencias:
                grafo.add_node(modelo)  
            for dep in dependencias:
                grafo.add_edge(dep, modelo)
        
        # Ordenar modelos topologicamente
        try:
            modelos_ordenados = list(nx.topological_sort(grafo))
        except nx.NetworkXUnfeasible:
            ciclo = nx.find_cycle(grafo)
            if ciclo:
                str_ciclo = '\n'.join([f"{x[0]._meta.model_name} -> {x[1]._meta.model_name}" for x in ciclo])
                raise Exception(f"Dependencia cíclica detectada:\n{str_ciclo}")
            raise Exception(f"Error al ordenar los modelos topologicamente")

        return modelos_ordenados

    def _obtener_dependecias(self, modelo):
        dependencias = []
        for campo in modelo._meta.fields + modelo._meta.many_to_many:
            if campo.related_model:
                dependencias.append(campo.related_model)

        return dependencias