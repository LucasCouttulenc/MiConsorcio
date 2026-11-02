"""
Escenario de la app gastos.

Los modelos de gastos dependen entre sí en forma circular *por los datos*
(no por las FK): la liquidación necesita el total de sus gastos, el detalle
por UF necesita las cuotas del convenio, el convenio necesita la deuda de los
detalles, los pagos necesitan los intereses... Por eso el escenario se simula
una sola vez, en orden cronológico y con las mismas reglas que la app:
procesar_liquidacion_periodo (services.py), aplicar_saldo_a_favor,
cobrar_cuotas_convenio, imputar_pago con repartir_capital (reparto.py) e
interés simple por mes o fracción (models.py). Cada fixture de gastos solo toma su parte del resultado y
resuelve las pk con los métodos del administrador.

Situaciones que deja armadas en cada consorcio (UF en orden de pk):
  - UF 1: morosa, no pagó los últimos 3 períodos.
  - UF 2: al día, con el pago del último período pendiente de validación.
  - UF 3 y 4: rotan entre convenio de pago, pago con interés por atraso,
    saldo a favor y pago rechazado.
  - El resto: al día. El último período puede estar todavía sin pagar si no venció.
"""
import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP, ROUND_UP
from functools import partial

from django.conf import settings
from django.utils import timezone

from consorcios.models import Consorcio, GrupoProrrateo, Personal, Rubro, TipoReparto, UnidadFuncional
from gastos.models import ClaseGasto, TipoGasto, periodo_a_meses, sumar_meses
from gastos.reparto import montos_del_cupon, repartir_capital
from .consorcios_rubro import (
    RUBRO_ADMINISTRACION, RUBRO_MANTENIMIENTO, RUBRO_REMUNERACIONES, RUBRO_SERVICIOS_PUBLICOS,
)

# Todo fixture de gastos debe declarar estos modelos en dependencias_extra:
# cualquiera de ellos puede ser el primero en pedir el escenario.
DEPENDENCIAS_ESCENARIO = (Consorcio, UnidadFuncional, GrupoProrrateo, Rubro, Personal)

CANTIDAD_PERIODOS = 6
INFLACION_MENSUAL = Decimal('0.025')
DIA_VENCIMIENTO = 10
# Caja: el consorcio arranca con un colchón de meses de gastos ordinarios, porque los gastos
# de un mes se pagan antes de cobrar sus expensas (vencen el mes siguiente).
MESES_DE_COLCHON = Decimal('2')
CAJA_CHICA = Decimal('150000.00')        # efectivo que queda en la administración
DIAS_DE_DEPOSITO = (7, 14, 21, 28)       # cuándo se deposita en el banco la cobranza en efectivo
GASTOS_EN_EFECTIVO = {
    'Compra de artículos de limpieza',
    'Cerrajería: cambio de cerradura de la puerta de entrada',
}
EXCEDENTE_SALDO_A_FAVOR = Decimal('25000.00')
CUOTAS_CONVENIO = 6
INTERES_CONVENIO = Decimal('5.00')

CENTAVO = Decimal('0.01')
DIEZMILESIMO = Decimal('0.0001')
CERO = Decimal('0')
PARTES = ('convenio', 'ordinario', 'extraordinario', 'fondo')

MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio',
         'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']

ENCARGADO = object()  # marcador: el concepto lleva el nombre del encargado
LIMPIEZA = object()   # marcador: el proveedor es la empresa de limpieza del fixture de Personal

# (rubro, columna, concepto, monto del último período, clase)
GASTOS_FIJOS = [
    (RUBRO_REMUNERACIONES, 'A', ENCARGADO, 1250000, ClaseGasto.GASTO),
    (RUBRO_REMUNERACIONES, 'A', 'Cargas sociales (F.931)', 380000, ClaseGasto.GASTO),
    (RUBRO_REMUNERACIONES, 'A', 'Aportes SUTERH y FATERYH', 45000, ClaseGasto.GASTO),
    (RUBRO_SERVICIOS_PUBLICOS, 'A', 'Edenor - electricidad de espacios comunes', 210000, ClaseGasto.SERVICIO),
    (RUBRO_SERVICIOS_PUBLICOS, 'A', 'AySA - agua corriente', 95000, ClaseGasto.SERVICIO),
    (RUBRO_ADMINISTRACION, 'A', 'Seguro integral del edificio', 85000, ClaseGasto.GASTO),
    (RUBRO_ADMINISTRACION, 'A', 'Gastos bancarios', 18000, ClaseGasto.GASTO),
]

# (concepto, proveedor, rubro, columna, monto sugerido, frecuencia, meses de inicio respecto
#  del primer período, activo, clase)
SERVICIOS_RECURRENTES = [
    ('Abono de mantenimiento de ascensores', 'Ascensores Delta', RUBRO_MANTENIMIENTO, 'B',
     185000, 1, -12, True, ClaseGasto.SERVICIO),
    ('Servicio de limpieza', LIMPIEZA, RUBRO_MANTENIMIENTO, 'A', 420000, 1, -12, True, ClaseGasto.SERVICIO),
    ('Honorarios de administración', '', RUBRO_ADMINISTRACION, 'A', 160000, 1, -12, True, ClaseGasto.GASTO),
    ('Desinfección y control de plagas', 'Fumigaciones del Plata', RUBRO_MANTENIMIENTO, 'A',
     45000, 3, -2, True, ClaseGasto.SERVICIO),
    ('Limpieza y desinfección de tanques de agua', 'Tanques Limpios S.R.L.', RUBRO_MANTENIMIENTO, 'A',
     120000, 6, -3, True, ClaseGasto.SERVICIO),
    # Anual: no cae en los períodos liquidados, queda como próximo a proponer.
    ('Recarga y control de matafuegos', 'Matafuegos Express', RUBRO_MANTENIMIENTO, 'A',
     95000, 12, -4, True, ClaseGasto.SERVICIO),
    # Dado de baja antes del primer período.
    ('Vigilancia nocturna', 'Custodia Integral S.A.', RUBRO_ADMINISTRACION, 'A',
     350000, 1, -12, False, ClaseGasto.SERVICIO),
]

REPARACIONES = [
    ('Reparación de bomba de agua', 180000),
    ('Cambio de luminarias LED en palieres', 95000),
    ('Plomería: reparación de cañería de desagüe', 140000),
    ('Cerrajería: cambio de cerradura de la puerta de entrada', 65000),
    ('Pintura del hall de entrada', 210000),
    ('Compra de artículos de limpieza', 48000),
]
PROBABILIDAD_REPARACION = 0.4
PROBABILIDAD_TERRAZA = 0.2

# La obra en curso del fixture de obras: se cobra en cuotas extraordinarias y se avisa a los propietarios.
OBRA_EXTRAORDINARIA = 'Impermeabilización de terraza'
INICIO_OBRA_DIAS = 20
CUOTAS_OBRA = 3
MONTO_CUOTA_OBRA = Decimal('900000.00')

ROLES_ROTATIVOS = ['convenio', 'pago_tardio', 'saldo_a_favor', 'rechazado']
NOTA_RECHAZO = ('El comprobante adjunto no corresponde a una transferencia acreditada en la cuenta '
                'del consorcio. Por favor, volvé a cargar el pago.')


#####################################################################
#                       Acceso desde los fixtures                   #
#####################################################################

_escenario = None


def obtener_escenario(administrador):
    global _escenario
    if _escenario is None:
        _escenario = _Escenario(administrador)
    return _escenario


def a_json(valor):
    """Fechas, momentos y montos al formato que espera loaddata."""
    if isinstance(valor, datetime):
        return valor.isoformat()
    if isinstance(valor, (date, Decimal)):
        return str(valor)
    return valor


def id_liquidacion(adm, consorcio, periodo):
    from gastos.models import Liquidacion
    return adm.obtener_id(Liquidacion, consorcio=consorcio, periodo=periodo)


def id_detalle(adm, consorcio, periodo, unidad_funcional):
    from gastos.models import DetalleLiquidacionUF
    return adm.obtener_id(
        DetalleLiquidacionUF,
        liquidacion=id_liquidacion(adm, consorcio, periodo),
        unidad_funcional=unidad_funcional,
    )


def id_pago(adm, consorcio, clave_pago):
    from gastos.models import Pago
    unidad_funcional, periodo, fecha = clave_pago
    return adm.obtener_id(
        Pago,
        detalle_liquidacion=id_detalle(adm, consorcio, periodo, unidad_funcional),
        fecha_pago=str(fecha),
    )


#####################################################################
#                              Helpers                              #
#####################################################################

def _redondear(monto, unidad=CENTAVO):
    return monto.quantize(unidad, rounding=ROUND_HALF_UP)


def _redondear_cien(monto):
    return (monto / 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP) * 100


def _periodo(fecha):
    return f'{fecha.year:04d}-{fecha.month:02d}'


def _primer_dia(periodo):
    anio, mes = map(int, periodo.split('-'))
    return date(anio, mes, 1)


def _ultimo_dia(periodo):
    return sumar_meses(_primer_dia(periodo), 1) - timedelta(days=1)


def _meses_de_atraso(vencimiento, hoy):
    """Igual que DetalleLiquidacionUF.meses_de_atraso."""
    if not vencimiento or hoy <= vencimiento:
        return 0
    meses = (hoy.year - vencimiento.year) * 12 + hoy.month - vencimiento.month
    return meses + 1 if hoy.day > vencimiento.day else meses


def _momento(fecha, hora=9, minuto=0):
    momento = datetime.combine(fecha, time(hora, minuto))
    return timezone.make_aware(momento) if settings.USE_TZ else momento


def pesos(monto):
    """Como services.formatear_moneda: '$ 1.234,50'."""
    texto = f'{monto:,.2f}'
    return '$ ' + texto.replace(',', 'X').replace('.', ',').replace('X', '.')


def nombre_periodo(periodo):
    """'2026-09' -> 'Septiembre 2026'."""
    anio, mes = map(int, periodo.split('-'))
    return f'{MESES[mes - 1].capitalize()} {anio}'


#####################################################################
#                             Escenario                             #
#####################################################################

class _Escenario:
    def __init__(self, adm):
        self.adm = adm
        self.rng = random.Random()
        self.ahora = (timezone.localtime() if settings.USE_TZ else datetime.now()).replace(microsecond=0)
        self.hoy = self.ahora.date()

        # Los últimos CANTIDAD_PERIODOS meses cerrados, del más viejo al más nuevo.
        ultimo = sumar_meses(self.hoy.replace(day=1), -1)
        self.periodos = [_periodo(sumar_meses(ultimo, -i)) for i in range(CANTIDAD_PERIODOS - 1, -1, -1)]

        self.servicios = []
        self.liquidaciones = []
        self.gastos = []
        self.distribuciones = []
        self.detalles = []
        self.convenios = []
        self.cuotas = []
        self.pagos = []
        self.imputaciones = []
        self.notificaciones = []
        self.novedades = []
        self.movimientos = []

        for indice, consorcio in enumerate(adm.obtener_ids(Consorcio)):
            _EscenarioConsorcio(self, consorcio, indice).generar()

    def tope_ahora(self, momento):
        return min(momento, self.ahora)


class _EscenarioConsorcio:
    def __init__(self, escenario, consorcio, indice):
        self.esc = escenario
        self.adm = adm = escenario.adm
        self.rng = escenario.rng
        self.consorcio = consorcio
        self.indice = indice
        self.periodos = escenario.periodos

        self.tasa = Decimal(str(adm.obtener_valor(Consorcio, consorcio, 'tasa_interes_mensual')))
        self.fondo_nombre = adm.obtener_valor(Consorcio, consorcio, 'fondo_reserva_nombre') or ''
        self.fondo_porcentaje = Decimal(str(adm.obtener_valor(Consorcio, consorcio, 'fondo_reserva_porcentaje')))

        self.ufs = adm.obtener_ids(UnidadFuncional, consorcio=consorcio)
        self.alicuota = {uf: Decimal(str(adm.obtener_valor(UnidadFuncional, uf, 'alicuota'))) for uf in self.ufs}
        self.propietario = {uf: adm.obtener_valor(UnidadFuncional, uf, 'propietario') for uf in self.ufs}
        self.etiqueta = {
            uf: f"{adm.obtener_valor(UnidadFuncional, uf, 'piso')}° "
                f"{adm.obtener_valor(UnidadFuncional, uf, 'departamento')}"
            for uf in self.ufs
        }

        # (rubro, código de columna) -> (pk del grupo, UF que pagan)
        self.grupos = {}
        for grupo in adm.obtener_ids(GrupoProrrateo, consorcio=consorcio):
            rubro = adm.obtener_valor(Rubro, adm.obtener_valor(GrupoProrrateo, grupo, 'rubro'), 'nombre')
            codigo = adm.obtener_valor(GrupoProrrateo, grupo, 'codigo')
            self.grupos[(rubro, codigo)] = (grupo, self._pagadores(grupo))

        encargados = adm.obtener_ids(Personal, consorcio=consorcio, cargo='Encargado')
        self.concepto_encargado = 'Sueldo del encargado'
        if encargados:
            nombre = adm.obtener_valor(Personal, encargados[0], 'nombre')
            apellido = adm.obtener_valor(Personal, encargados[0], 'apellido')
            self.concepto_encargado = f'Sueldo del encargado ({nombre} {apellido})'

        tercerizados = adm.obtener_ids(Personal, consorcio=consorcio, tipo_contratacion='tercerizado')
        self.empresa_limpieza = (
            adm.obtener_valor(Personal, tercerizados[0], 'empresa_tercerizada') if tercerizados else ''
        )

        # periodo -> (cierre, emisión, primer vencimiento)
        self.fechas = {}
        for periodo in self.periodos:
            cierre = _ultimo_dia(periodo)
            emision = cierre + timedelta(days=1)
            self.fechas[periodo] = (cierre, emision, emision.replace(day=DIA_VENCIMIENTO))

        self.servicios = []
        self.detalles = {}       # (uf, periodo) -> estado del detalle
        self.imputaciones = []
        self.convenios = {}      # uf -> convenio con sus cuotas
        self.pagos = []
        self.gastos = []
        self.cobros_caja = []

    #################################################################
    #                          Orquestación                         #
    #################################################################

    def generar(self):
        self._definir_servicios()

        eventos = []
        for k, periodo in enumerate(self.periodos):
            eventos.append((self.fechas[periodo][1], 0, partial(self._cerrar_liquidacion, k)))
        self._planificar_pagos(eventos)

        for _, _, _, accion in sorted((f, o, i, a) for i, (f, o, a) in enumerate(eventos)):
            accion()

        self._volcar()
        self._generar_caja()
        self._generar_notificaciones()
        self._generar_novedades()

    #################################################################
    #                      Servicios y gastos                       #
    #################################################################

    def _pagadores(self, grupo):
        tipo = self.adm.obtener_valor(GrupoProrrateo, grupo, 'tipo_reparto')
        unidades = set(self.adm.obtener_valor(GrupoProrrateo, grupo, 'unidades') or [])
        if tipo == TipoReparto.PARCIAL:
            return [uf for uf in self.ufs if uf not in unidades]
        if tipo == TipoReparto.PARTICULAR:
            return [uf for uf in self.ufs if uf in unidades]
        return list(self.ufs)

    def _definir_servicios(self):
        primero = _primer_dia(self.periodos[0])
        for concepto, proveedor, rubro, codigo, monto, frecuencia, inicio, activo, clase in SERVICIOS_RECURRENTES:
            servicio = {
                'consorcio': self.consorcio,
                'concepto': concepto,
                'proveedor': self.empresa_limpieza if proveedor is LIMPIEZA else proveedor,
                'columna': self.grupos[(rubro, codigo)][0],
                'tipo': TipoGasto.ORDINARIO,
                'monto_sugerido': Decimal(monto).quantize(CENTAVO),
                'frecuencia_meses': frecuencia,
                'periodo_inicio': _periodo(sumar_meses(primero, inicio)),
                'periodo_fin': '' if activo else _periodo(sumar_meses(primero, -1)),
                'activo': activo,
                # Solo para el escenario
                '_rubro': rubro, '_codigo': codigo, '_clase': clase,
            }
            self.servicios.append(servicio)
            self.esc.servicios.append(servicio)

    def _corresponde(self, servicio, periodo):
        """Igual que ServicioRecurrente.corresponde_en."""
        if not servicio['activo']:
            return False
        actual = periodo_a_meses(periodo)
        inicio = periodo_a_meses(servicio['periodo_inicio'])
        if actual < inicio:
            return False
        if servicio['periodo_fin'] and actual > periodo_a_meses(servicio['periodo_fin']):
            return False
        return (actual - inicio) % servicio['frecuencia_meses'] == 0

    def _fecha_en(self, periodo, desde=3, hasta=25):
        return _primer_dia(periodo).replace(day=self.rng.randint(desde, hasta))

    def _gastos_del_periodo(self, k):
        periodo = self.periodos[k]
        factor = (1 + INFLACION_MENSUAL) ** (k - (CANTIDAD_PERIODOS - 1))
        gastos = []

        def agregar(rubro, codigo, concepto, monto, clase, fecha, tipo=TipoGasto.ORDINARIO, servicio=None):
            gastos.append({
                'rubro': rubro, 'codigo': codigo, 'concepto': concepto, 'monto': monto.quantize(CENTAVO),
                'clase': clase, 'fecha_comprobante': fecha, 'tipo': tipo, 'servicio': servicio,
            })

        for rubro, codigo, concepto, monto, clase in GASTOS_FIJOS:
            es_sueldo = concepto is ENCARGADO
            agregar(
                rubro, codigo, self.concepto_encargado if es_sueldo else concepto,
                _redondear_cien(Decimal(monto) * factor), clase,
                _ultimo_dia(periodo) if es_sueldo else self._fecha_en(periodo),
            )

        for servicio in self.servicios:
            if not self._corresponde(servicio, periodo):
                continue
            variacion = Decimal(str(round(self.rng.uniform(0.97, 1.03), 4)))
            agregar(
                servicio['_rubro'], servicio['_codigo'], servicio['concepto'],
                _redondear_cien(servicio['monto_sugerido'] * factor * variacion), servicio['_clase'],
                self._fecha_en(periodo), servicio=servicio['concepto'],
            )

        if self.rng.random() < PROBABILIDAD_REPARACION:
            concepto, monto = self.rng.choice(REPARACIONES)
            agregar(RUBRO_MANTENIMIENTO, 'A', concepto, _redondear_cien(Decimal(monto) * factor),
                    ClaseGasto.GASTO, self._fecha_en(periodo))

        if self.rng.random() < PROBABILIDAD_TERRAZA:
            agregar(RUBRO_MANTENIMIENTO, 'C', 'Reparación de membrana en terraza de uso exclusivo',
                    _redondear_cien(Decimal(150000) * factor), ClaseGasto.GASTO, self._fecha_en(periodo))

        # Las últimas cuotas de la obra, que todavía sigue en curso.
        cuota_obra = k - (CANTIDAD_PERIODOS - CUOTAS_OBRA) + 1
        if 1 <= cuota_obra < CUOTAS_OBRA:
            agregar(RUBRO_MANTENIMIENTO, 'A', f'{OBRA_EXTRAORDINARIA} - cuota {cuota_obra} de {CUOTAS_OBRA}',
                    MONTO_CUOTA_OBRA, ClaseGasto.GASTO, self._fecha_en(periodo, 1, 5),
                    tipo=TipoGasto.EXTRAORDINARIO)

        return gastos

    def _repartir_por_alicuota(self, monto, ufs):
        """Como services.py: proporcional a la alícuota, la última UF absorbe el redondeo."""
        suma = sum(self.alicuota[uf] for uf in ufs)
        reparto = []
        asignado = CERO
        for indice, uf in enumerate(ufs):
            parte = _redondear(monto * self.alicuota[uf] / suma) if indice < len(ufs) - 1 else monto - asignado
            asignado += parte
            reparto.append((uf, parte))
        return reparto

    def _distribuir(self, monto, pagadores):
        """Filas de DetalleGastoUF: (uf, porcentaje del gasto, monto), como procesar_liquidacion_periodo."""
        return [
            (uf, (parte * 100 / monto).quantize(DIEZMILESIMO) if monto else CERO, parte)
            for uf, parte in self._repartir_por_alicuota(monto, pagadores)
        ]

    #################################################################
    #               Cierre de liquidación (como la app)             #
    #################################################################

    def _cerrar_liquidacion(self, k):
        periodo = self.periodos[k]
        cierre, emision, vencimiento = self.fechas[periodo]
        por_uf = {uf: {TipoGasto.ORDINARIO: CERO, TipoGasto.EXTRAORDINARIO: CERO} for uf in self.ufs}
        totales = {TipoGasto.ORDINARIO: CERO, TipoGasto.EXTRAORDINARIO: CERO}

        for posicion, gasto in enumerate(self._gastos_del_periodo(k), start=1):
            grupo, pagadores = self.grupos[(gasto['rubro'], gasto['codigo'])]
            for uf, porcentaje, asignado in self._distribuir(gasto['monto'], pagadores):
                self.esc.distribuciones.append({
                    'consorcio': self.consorcio, 'periodo': periodo, 'posicion': posicion,
                    'unidad_funcional': uf, 'porcentaje_aplicado': porcentaje, 'monto_asignado': asignado,
                })
                por_uf[uf][gasto['tipo']] += asignado
            totales[gasto['tipo']] += gasto['monto']

            registro = {**gasto, 'consorcio': self.consorcio, 'periodo': periodo, 'posicion': posicion, 'grupo': grupo}
            self.gastos.append(registro)
            self.esc.gastos.append(registro)

        # Fondo de reserva: % del total de ordinarias, repartido entre todas las UF por alícuota.
        total_fondo = _redondear(totales[TipoGasto.ORDINARIO] * self.fondo_porcentaje / 100)
        fondo_por_uf = dict.fromkeys(self.ufs, CERO)
        if total_fondo > 0:
            fondo_por_uf.update(self._repartir_por_alicuota(total_fondo, self.ufs))

        for uf in self.ufs:
            ordinario = por_uf[uf][TipoGasto.ORDINARIO]
            fondo = fondo_por_uf[uf]
            self.detalles[(uf, periodo)] = {
                'uf': uf, 'periodo': periodo, 'k': k, 'vencimiento': vencimiento, 'convenio': None,
                'montos': {
                    'convenio': CERO,
                    'ordinario': ordinario,
                    'extraordinario': por_uf[uf][TipoGasto.EXTRAORDINARIO],
                    'fondo': fondo,
                },
            }

        for uf in self.ufs:
            self._aplicar_saldo_a_favor((uf, periodo))
        self._cobrar_cuotas_convenio(periodo)

        self.esc.liquidaciones.append({
            'consorcio': self.consorcio,
            'periodo': periodo,
            'fecha_emision': emision,
            'fecha_cierre': cierre,
            'fecha_vencimiento_1': vencimiento,
            'total_ordinario': totales[TipoGasto.ORDINARIO].quantize(CENTAVO),
            'total_extraordinario': totales[TipoGasto.EXTRAORDINARIO].quantize(CENTAVO),
            'fondo_reserva_nombre': self.fondo_nombre or 'Fondo de reserva',
            'fondo_reserva_porcentaje': self.fondo_porcentaje,
            'total_fondo_reserva': total_fondo,
            'actualizada': _momento(emision, 10),
        })

    def _aplicar_saldo_a_favor(self, clave):
        """Como aplicar_saldo_a_favor: el excedente se toma como adelanto de las ordinarias."""
        detalle = self.detalles[clave]
        tope = detalle['montos']['ordinario']
        excedentes = [imp for imp in self.imputaciones
                      if imp['concepto'] == 'excedente' and imp['pago'][0] == detalle['uf']]
        for excedente in excedentes:
            if tope <= 0:
                break
            monto = min(excedente['monto'], tope)
            self._imputar_parte(excedente['pago'], excedente['fecha'], clave, 'adelanto', 'ordinario', monto)
            tope -= monto
            excedente['monto'] -= monto
            if excedente['monto'] <= 0:
                self.imputaciones.remove(excedente)

    def _cobrar_cuotas_convenio(self, periodo):
        """Como cobrar_cuotas_convenio, para convenios vigentes."""
        for uf, convenio in self.convenios.items():
            if convenio['estado'] != 'vigente' or convenio['periodo_inicio'] > periodo:
                continue
            sin_cobrar = [cuota for cuota in convenio['cuotas'] if cuota['periodo'] is None]
            if sin_cobrar:
                sin_cobrar[0]['periodo'] = periodo
                self.detalles[(uf, periodo)]['montos']['convenio'] += sin_cobrar[0]['monto']

    #################################################################
    #                 Deuda e intereses (como la app)               #
    #################################################################

    def _total(self, clave):
        return sum(self.detalles[clave]['montos'].values(), CERO)

    def _imputaciones_de(self, clave, *conceptos):
        return [imp for imp in self.imputaciones if imp['detalle'] == clave and imp['concepto'] in conceptos]

    def _cancelado(self, clave, hasta=None):
        return sum((imp['monto'] for imp in self._imputaciones_de(clave, 'capital', 'adelanto')
                    if hasta is None or imp['fecha'] <= hasta), CERO)

    def _deuda(self, clave):
        if self.detalles[clave]['convenio']:
            return CERO
        return self._total(clave) - self._cancelado(clave)

    def _interes(self, clave, hoy):
        detalle = self.detalles[clave]
        if detalle['convenio'] or not self.tasa:
            return CERO
        vencimiento = detalle['vencimiento']
        devengado = sum(
            (self._total(clave) - self._cancelado(clave, sumar_meses(vencimiento, mes))
             for mes in range(_meses_de_atraso(vencimiento, hoy))),
            CERO,
        ) * self.tasa / 100
        pagados = sum((imp['monto'] for imp in self._imputaciones_de(clave, 'interes')), CERO)
        return max(_redondear(devengado) - pagados, CERO)

    def _pendiente_por_parte(self, clave):
        pagado = dict.fromkeys(PARTES, CERO)
        for imp in self._imputaciones_de(clave, 'capital', 'adelanto'):
            pagado[imp['parte'] or 'ordinario'] += imp['monto']
        montos = self.detalles[clave]['montos']
        cupon = montos_del_cupon(self._total(clave), montos['extraordinario'], montos['fondo'], montos['convenio'])
        return {parte: max(monto - pagado[parte], CERO) for parte, monto in cupon.items()}

    def _imputar_parte(self, clave_pago, fecha, clave_detalle, concepto, parte, monto):
        self.imputaciones.append({
            'pago': clave_pago, 'fecha': fecha, 'detalle': clave_detalle,
            'concepto': concepto, 'parte': parte, 'monto': monto,
        })

    def _imputar_pago(self, clave_pago, uf, fecha, monto):
        """Como imputar_pago: del período más viejo al más nuevo, primero interés y después capital."""
        restante = monto
        for clave in sorted((c for c in self.detalles if c[0] == uf), key=lambda c: c[1]):
            interes = min(restante, self._interes(clave, fecha))
            if interes > 0:
                self._imputar_parte(clave_pago, fecha, clave, 'interes', '', interes)
                restante -= interes
            capital = min(restante, self._deuda(clave))
            if capital > 0:
                for parte, monto_parte in repartir_capital(self._pendiente_por_parte(clave), capital):
                    self._imputar_parte(clave_pago, fecha, clave, 'capital', parte, monto_parte)
                restante -= capital
            if restante <= 0:
                break
        if restante > 0:
            self._imputar_parte(clave_pago, fecha, None, 'excedente', '', restante)

    #################################################################
    #                       Pagos y convenios                       #
    #################################################################

    def _a_termino(self, k):
        _, emision, vencimiento = self.fechas[self.periodos[k]]
        hasta = min(vencimiento, self.esc.hoy)
        return emision + timedelta(days=self.rng.randint(0, max((hasta - emision).days, 0)))

    def _medio(self):
        return self.rng.choices(['transferencia', 'deposito', 'efectivo'], weights=[70, 15, 15])[0]

    def _planificar_pagos(self, eventos):
        roles = {
            self.ufs[0]: 'moroso',
            self.ufs[1]: 'pago_pendiente',
            self.ufs[2]: ROLES_ROTATIVOS[self.indice % len(ROLES_ROTATIVOS)],
            self.ufs[3]: ROLES_ROTATIVOS[(self.indice + 1) % len(ROLES_ROTATIVOS)],
        }
        for uf in self.ufs:
            for pago in self._plan_de_pagos(uf, roles.get(uf, 'al_dia'), eventos):
                eventos.append((pago['fecha'], 2, partial(self._registrar_pago, pago)))

    def _plan_de_pagos(self, uf, rol, eventos):
        n = CANTIDAD_PERIODOS
        ultimo_vencimiento = self.fechas[self.periodos[-1]][2]
        # El último período todavía puede estar sin pagar si no venció.
        paga_ultimo = self.esc.hoy > ultimo_vencimiento or self.rng.random() < 0.6
        pagos = []

        def pago(k, fecha=None, estado='validado', medio=None, notas=''):
            pagos.append({
                'uf': uf, 'k': k, 'fecha': fecha or self._a_termino(k), 'estado': estado,
                'medio': medio or self._medio(), 'extra': CERO, 'notas': notas,
            })

        def al_dia(desde=0, salvo=()):
            for k in range(desde, n):
                if k in salvo or (k == n - 1 and not paga_ultimo):
                    continue
                pago(k)

        if rol == 'moroso':
            for k in range(n - 3):
                pago(k)

        elif rol == 'pago_pendiente':
            for k in range(n - 1):
                pago(k)
            pago(n - 1, estado='pendiente', medio='transferencia')

        elif rol == 'convenio':
            # No paga los dos primeros períodos; los refinancia después del segundo vencimiento.
            fecha_alta = self.fechas[self.periodos[1]][2] + timedelta(days=12)
            eventos.append((fecha_alta, 1, partial(self._crear_convenio, uf, fecha_alta, self.periodos[2])))
            al_dia(desde=2)

        elif rol == 'pago_tardio':
            k_tarde = n - 3
            vencimiento = self.fechas[self.periodos[k_tarde]][2]
            al_dia(salvo=(k_tarde,))
            pago(k_tarde, fecha=vencimiento + timedelta(days=self.rng.randint(5, 15)))

        elif rol == 'rechazado':
            k_rechazo = n - 2
            _, emision, vencimiento = self.fechas[self.periodos[k_rechazo]]
            primer_intento = emision + timedelta(days=self.rng.randint(0, (vencimiento - emision).days - 4))
            al_dia(salvo=(k_rechazo,))
            pago(k_rechazo, fecha=primer_intento, estado='rechazado', medio='transferencia', notas=NOTA_RECHAZO)
            pago(k_rechazo, fecha=primer_intento + timedelta(days=self.rng.randint(1, 4)), medio='transferencia')

        elif rol == 'saldo_a_favor':
            al_dia()
            max(pagos, key=lambda p: p['fecha'])['extra'] = EXCEDENTE_SALDO_A_FAVOR

        else:
            al_dia()

        return pagos

    def _registrar_pago(self, pago):
        uf = pago['uf']
        periodo = self.periodos[pago['k']]
        clave_detalle = (uf, periodo)
        monto = self._deuda(clave_detalle) + self._interes(clave_detalle, pago['fecha']) + pago['extra']
        if monto <= 0:
            return

        clave_pago = (uf, periodo, pago['fecha'])
        registro = _momento(pago['fecha'], self.rng.randint(8, 21), self.rng.randint(0, 59))
        self.pagos.append({
            'consorcio': self.consorcio,
            'clave': clave_pago,
            'unidad_funcional': uf,
            'periodo': periodo,
            'fecha_pago': pago['fecha'],
            'monto_pagado': monto,
            'medio_pago': pago['medio'],
            'estado': pago['estado'],
            'fecha_registro': self.esc.tope_ahora(registro),
            'notas_admin': pago['notas'],
        })
        if pago['estado'] == 'validado':
            desde = len(self.imputaciones)
            self._imputar_pago(clave_pago, uf, pago['fecha'], monto)
            self._registrar_cobro_en_caja(pago, periodo, self.imputaciones[desde:])

    def _registrar_cobro_en_caja(self, pago, periodo, imputaciones):
        """
        Como al validar un pago: lo extraordinario y el fondo entran como extraordinario,
        el resto (ordinarias, cuota de convenio, intereses y saldo a favor) como ordinario.
        """
        montos = {'ordinario': CERO, 'extraordinario': CERO}
        for imputacion in imputaciones:
            es_extraordinario = imputacion['concepto'] == 'capital' and imputacion['parte'] in ('extraordinario', 'fondo')
            montos['extraordinario' if es_extraordinario else 'ordinario'] += imputacion['monto']
        for tipo, monto in montos.items():
            if monto > 0:
                self.cobros_caja.append({
                    'fecha': pago['fecha'],
                    'concepto': f"Cobro de expensas UF {self.etiqueta[pago['uf']]} - período {periodo}",
                    'monto': monto,
                    'tipo': tipo,
                    'medio_pago': 'efectivo' if pago['medio'] == 'efectivo' else 'transferencia',
                })

    def _crear_convenio(self, uf, fecha_alta, periodo_inicio):
        """Como crear_convenio: congela la deuda vencida y la divide en cuotas iguales."""
        claves = [
            clave for clave in sorted((c for c in self.detalles if c[0] == uf), key=lambda c: c[1])
            if not self.detalles[clave]['convenio'] and self._deuda(clave) > 0
            and self.detalles[clave]['vencimiento'] < fecha_alta
        ]
        if not claves:
            return
        capital = sum((self._deuda(clave) for clave in claves), CERO)
        intereses = sum((self._interes(clave, fecha_alta) for clave in claves), CERO)
        deuda = capital + intereses
        total = _redondear(deuda + deuda * INTERES_CONVENIO / 100)
        cuota = _redondear(total / CUOTAS_CONVENIO)

        for clave in claves:
            self.detalles[clave]['convenio'] = uf

        self.convenios[uf] = {
            'consorcio': self.consorcio,
            'unidad_funcional': uf,
            'fecha_alta': fecha_alta,
            'capital': capital,
            'intereses': intereses,
            'interes_porcentaje': INTERES_CONVENIO,
            'cantidad_cuotas': CUOTAS_CONVENIO,
            'cuotas_para_caducidad': 2,
            'periodo_inicio': periodo_inicio,
            'estado': 'vigente',
            'cuotas': [
                {
                    'consorcio': self.consorcio,
                    'unidad_funcional': uf,
                    'numero': numero,
                    'monto': cuota if numero < CUOTAS_CONVENIO else total - cuota * (CUOTAS_CONVENIO - 1),
                    'periodo': None,
                }
                for numero in range(1, CUOTAS_CONVENIO + 1)
            ],
        }

    #################################################################
    #                    Volcado y datos derivados                  #
    #################################################################

    def _volcar(self):
        for (uf, periodo), detalle in self.detalles.items():
            montos = detalle['montos']
            self.esc.detalles.append({
                'consorcio': self.consorcio,
                'periodo': periodo,
                'unidad_funcional': uf,
                'alicuota': self.alicuota[uf],
                'monto_ordinario': montos['ordinario'],
                'monto_extraordinario': montos['extraordinario'],
                'monto_fondo_reserva': montos['fondo'],
                'monto_convenio': montos['convenio'],
                'monto_total': self._total((uf, periodo)),
                'convenio': detalle['convenio'],
            })
        for convenio in self.convenios.values():
            self.esc.convenios.append(convenio)
            self.esc.cuotas.extend(convenio['cuotas'])
        self.esc.pagos.extend(self.pagos)
        for imputacion in self.imputaciones:
            self.esc.imputaciones.append({**imputacion, 'consorcio': self.consorcio})

    def _generar_caja(self):
        hoy = self.esc.hoy
        inicio = _primer_dia(self.periodos[0])
        ordinarios_primer_mes = sum(
            (g['monto'] for g in self.gastos if g['periodo'] == self.periodos[0] and g['tipo'] == TipoGasto.ORDINARIO),
            CERO,
        )
        colchon = (ordinarios_primer_mes * MESES_DE_COLCHON / 100000).quantize(Decimal('1'), rounding=ROUND_UP) * 100000

        def movimiento(fecha, concepto, monto, tipo='ordinario', medio='transferencia'):
            return {'fecha': fecha, 'concepto': concepto[:200], 'monto': monto, 'tipo': tipo, 'medio_pago': medio}

        movimientos = [
            movimiento(inicio, 'Saldo inicial en banco', colchon),
            movimiento(inicio, 'Saldo inicial de caja chica', CAJA_CHICA, medio='efectivo'),
            # Lo extraordinario acumulado de antes: alcanza para adelantarle una cuota de la obra al proveedor.
            movimiento(inicio, 'Saldo inicial extraordinario (fondo acumulado)', MONTO_CUOTA_OBRA, tipo='extraordinario'),
        ]

        # Cada gasto se paga unos días después del comprobante. Las cuotas de la obra se le
        # pagan al proveedor con lo recaudado, después del vencimiento de esa expensa.
        # Si la fecha de pago todavía no llegó, el gasto queda impago y fuera de caja.
        for gasto in self.gastos:
            if gasto['tipo'] == TipoGasto.EXTRAORDINARIO:
                fecha_pago = self.fechas[gasto['periodo']][2] + timedelta(days=self.rng.randint(3, 10))
            else:
                dias = self.rng.randint(1, 4) if gasto['concepto'] == self.concepto_encargado else self.rng.randint(2, 8)
                fecha_pago = gasto['fecha_comprobante'] + timedelta(days=dias)
            gasto['pagado'] = gasto['en_caja'] = fecha_pago <= hoy
            if gasto['pagado']:
                medio = 'efectivo' if gasto['concepto'] in GASTOS_EN_EFECTIVO else 'transferencia'
                movimientos.append(movimiento(fecha_pago, f"Pago: {gasto['concepto']}", -gasto['monto'], gasto['tipo'], medio))

        movimientos.extend(self.cobros_caja)
        movimientos.sort(key=lambda m: m['fecha'])

        # Dos veces por mes se deposita en el banco la cobranza en efectivo, salvo la caja chica.
        con_depositos = []
        efectivo = CERO
        fechas_deposito = sorted(
            date(f.year, f.month, dia)
            for f in {_primer_dia(p) for p in self.periodos + [_periodo(hoy)]}
            for dia in DIAS_DE_DEPOSITO
            if inicio <= date(f.year, f.month, dia) <= hoy
        )
        pendientes = list(movimientos)
        for fecha in fechas_deposito + [None]:
            while pendientes and (fecha is None or pendientes[0]['fecha'] <= fecha):
                actual = pendientes.pop(0)
                if actual['medio_pago'] == 'efectivo':
                    efectivo += actual['monto']
                con_depositos.append(actual)
            if fecha and efectivo > CAJA_CHICA:
                deposito = efectivo - CAJA_CHICA
                con_depositos.append(movimiento(fecha, 'Depósito en banco de la cobranza en efectivo', -deposito, medio='efectivo'))
                con_depositos.append(movimiento(fecha, 'Depósito en banco de la cobranza en efectivo', deposito))
                efectivo = CAJA_CHICA

        for actual in con_depositos:
            self.esc.movimientos.append({**actual, 'consorcio': self.consorcio})

    def _leida(self, creada, probabilidad):
        if self.rng.random() >= probabilidad:
            return None
        leida = creada + timedelta(hours=self.rng.randint(1, 72))
        return leida if leida <= self.esc.ahora else None

    def _generar_notificaciones(self):
        for (uf, periodo), detalle in self.detalles.items():
            propietario = self.propietario[uf]
            if propietario is None:
                continue
            creada = _momento(self.fechas[periodo][1], 10)
            es_ultimo = periodo == self.periodos[-1]
            self.esc.notificaciones.append({
                'consorcio': self.consorcio,
                'propietario': propietario,
                'periodo': periodo,
                'unidad_funcional': uf,
                'creada': creada,
                'leida_en': self._leida(creada, 0.4 if es_ultimo else 0.9),
            })

    def _generar_novedades(self):
        ahora = self.esc.ahora
        propietarios = list(dict.fromkeys(p for p in self.propietario.values() if p is not None))
        novedades = []

        def novedad(propietario, tipo, texto, detalle, creada, unidad_funcional=None, probabilidad_leida=0.5):
            novedades.append({
                'consorcio': self.consorcio,
                'propietario': propietario,
                'unidad_funcional': unidad_funcional,
                'tipo': tipo,
                'texto': texto[:200],
                'detalle': detalle[:200],
                'creada': creada,
                'leida_en': self._leida(creada, probabilidad_leida),
            })

        # Avisos para todo el consorcio
        for propietario in propietarios:
            novedad(propietario, 'obra', f'Comenzó la obra: {OBRA_EXTRAORDINARIA}', '',
                    ahora - timedelta(days=INICIO_OBRA_DIAS), probabilidad_leida=0.8)
            novedad(propietario, 'aviso', 'Corte de agua el jueves de 9 a 13 hs por mantenimiento de la bomba', '',
                    ahora - timedelta(days=2), probabilidad_leida=0.2)

        # Pagos de los dos últimos períodos
        for pago in self.pagos:
            uf = pago['unidad_funcional']
            if self.propietario[uf] is None or pago['periodo'] not in self.periodos[-2:]:
                continue
            if pago['estado'] == 'pendiente':
                continue
            creada = self.esc.tope_ahora(pago['fecha_registro'] + timedelta(days=1))
            texto = 'Pago validado' if pago['estado'] == 'validado' else 'Pago rechazado'
            detalle = f"{pesos(pago['monto_pagado'])} de {nombre_periodo(pago['periodo'])}"
            novedad(self.propietario[uf], 'pago', texto, detalle, creada, unidad_funcional=uf)

        self.esc.novedades.extend(novedades)