from ..fixture import Fixture
from consorcios.models import GrupoProrrateo, Consorcio, Rubro, TipoReparto, UnidadFuncional
from .consorcios_rubro import RUBRO_MANTENIMIENTO

class FixtureDeGrupoProrrateo(Fixture):
    """
    Por consorcio:
      - Columna A (general) en cada rubro.
      - En mantenimiento, además:
          B - Ascensores (parcial): las UF del 1° piso quedan exentas.
          C - Terrazas de uso exclusivo (particular): solo pagan las UF del último piso.
    """

    def __init__(self):
        super().__init__(GrupoProrrateo)

    def campos(self):
        adm = self.administrador
        resultado = []

        for consorcio in adm.obtener_ids(Consorcio):
            for rubro in adm.obtener_ids(Rubro, consorcio=consorcio):
                resultado.append({
                    'consorcio': consorcio,
                    'rubro': rubro,
                    'codigo': 'A',
                    'nombre': 'General',
                    'tipo_reparto': TipoReparto.GENERAL,
                })

            ufs = adm.obtener_ids(UnidadFuncional, consorcio=consorcio)
            ultimo_piso = max(adm.obtener_valor(UnidadFuncional, uf, 'piso') for uf in ufs)
            mantenimiento = adm.obtener_id(Rubro, consorcio=consorcio, nombre=RUBRO_MANTENIMIENTO)

            resultado.append({
                'consorcio': consorcio,
                'rubro': mantenimiento,
                'codigo': 'B',
                'nombre': 'Ascensores',
                'tipo_reparto': TipoReparto.PARCIAL,
                'unidades': adm.obtener_ids(UnidadFuncional, consorcio=consorcio, piso=1),
            })
            resultado.append({
                'consorcio': consorcio,
                'rubro': mantenimiento,
                'codigo': 'C',
                'nombre': 'Terrazas de uso exclusivo',
                'tipo_reparto': TipoReparto.PARTICULAR,
                'unidades': adm.obtener_ids(UnidadFuncional, consorcio=consorcio, piso=ultimo_piso),
            })

        return resultado