import importlib
import json
import networkx as nx
from pathlib import Path

CLAVE_MODELO = 'model'
CLAVE_PK = 'pk'
CLAVE_CAMPOS = 'fields'
SUFIJO_CONTIENE = '__contiene'

class AdministradorDeFixtures:
    _instacia = None

    def __new__(cls, *args, carpeta=None, **kwargs):
        if cls._instacia is None:
            if carpeta is None:
                raise ValueError("La carpeta de modelos no puede ser None")
            cls._instacia = super().__new__(cls, *args, **kwargs)
            cls._instacia._inicializar()
            cls._instacia.carpeta = carpeta
        return cls._instacia

    def _inicializar(self):
        self._diccionario_fixtures = {}
        self._fixtures = {}

    def agregar(self, fixture):
        self._fixtures[fixture.modelo] = fixture

    #################################################################
    #                    API DE CONSULTA (pública)                  #
    #################################################################
    # Los fixtures solo deberían acceder a otros fixtures con estos
    # métodos. Los filtros usan los nombres de campo tal cual se cargan
    # en el fixture (ej: 'consorcio', no 'consorcio_id'). 'pk' también
    # se puede usar como filtro.

    def obtener_ids(self, modelo, **filtros):
        """Ids de los registros que cumplen todos los filtros (todos si no hay filtros)."""
        return [registro[CLAVE_PK] for registro in self._filtrar(modelo, filtros)]

    def obtener_id(self, modelo, **filtros):
        """Id del único registro que cumple los filtros. Falla si hay cero o más de uno."""
        ids = self.obtener_ids(modelo, **filtros)
        if not ids:
            raise Exception(f"No se encontró un registro de {self._nombre(modelo)} con {filtros}")
        if len(ids) > 1:
            raise Exception(f"Hay {len(ids)} registros de {self._nombre(modelo)} con {filtros}; se esperaba uno")
        return ids[0]

    def obtener_valor(self, modelo, pk, campo):
        """Valor de un campo de un registro puntual."""
        for registro in self._registros(modelo):
            if registro[CLAVE_PK] == pk:
                return self._valor_de(registro, campo)
        raise Exception(f"No se encontró un registro de {self._nombre(modelo)} con pk={pk}")

    # Compatibilidad con los fixtures existentes
    def obtener_id_segun_campo(self, modelo, campo, valor):
        return self.obtener_id(modelo, **{campo: valor})

    def obtener_ids_segun_campo(self, modelo, campo, valor):
        return self.obtener_ids(modelo, **{campo: valor})

    #################################################################
    #                        Helpers internos                       #
    #################################################################

    def _nombre(self, modelo):
        return modelo._meta.label_lower

    def _registros(self, modelo):
        registros = self._diccionario_fixtures.get(modelo)
        if registros is None:
            raise Exception(
                f"No hay fixture generado para {self._nombre(modelo)}. "
                f"Verificá que exista el archivo y que el modelo que lo consulta dependa de él (FK/M2M)."
            )
        return registros

    def _valor_de(self, registro, campo):
        if campo == CLAVE_PK:
            return registro[CLAVE_PK]
        return registro[CLAVE_CAMPOS].get(campo)

    def _cumple(self, registro, campo, valor):
        if campo.endswith(SUFIJO_CONTIENE):
            lista = self._valor_de(registro, campo[:-len(SUFIJO_CONTIENE)]) or []
            return valor in lista
        return self._valor_de(registro, campo) == valor

    def _filtrar(self, modelo, filtros):
        return [
            registro for registro in self._registros(modelo)
            if all(self._cumple(registro, campo, valor) for campo, valor in filtros.items())
        ]

    #################################################################
    #                      Generación del archivo                   #
    #################################################################

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
        grafo = nx.DiGraph()

        # Crear grafo con modelos como nodos y dependencias como aristas
        for modelo, fixture in self._fixtures.items():
            dependencias = self._obtener_dependecias(modelo) + list(fixture.dependencias_extra)
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