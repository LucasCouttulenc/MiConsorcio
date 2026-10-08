from ..fixture import Fixture
from consorcios.models import GrupoProrrateo, Consorcio, Rubro


class FixtureDeGrupoProrrateo(Fixture):
    def __init__(self):
        super().__init__(GrupoProrrateo)

    def campos(self):
        fixture_consorcios = self.administrador._diccionario_fixtures.get(Consorcio, [])
        fixture_rubros = self.administrador._diccionario_fixtures.get(Rubro, [])

        rubros_por_consorcio = {}
        for reg in fixture_rubros:
            cid = reg['fields']['consorcio_id']
            rubros_por_consorcio.setdefault(cid, []).append(reg['pk'])

        resultado = []
        for consorcio_reg in fixture_consorcios:
            cid = consorcio_reg['pk']
            rubros = rubros_por_consorcio.get(cid, [])
            if not rubros:
                continue

            for rubro_id in rubros:
                for codigo in ['A', 'B', 'C']:
                    resultado.append({
                        'consorcio_id': cid,
                        'rubro_id': rubro_id,
                        'codigo': codigo,
                        'nombre': f'Columna {codigo}',
                        'tipo_reparto': 'general',
                    })
        return resultado