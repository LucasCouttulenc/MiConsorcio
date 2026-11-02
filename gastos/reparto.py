"""
Reparto de un pago parcial entre las partes de una expensa (story "Pago parcial").

Dentro de un mes, el capital pagado cancela primero la cuota del convenio y lo que sobra se reparte
entre ordinarias, extraordinarias y fondo de reserva en la proporción de lo que queda debiendo
de cada una (con el cupón sin pagar, es la proporción del cupón).

Son funciones sobre diccionarios para poder usarlas también desde las migraciones.
"""
from decimal import Decimal, ROUND_HALF_UP

COMPONENTES = ('convenio', 'ordinario', 'extraordinario', 'fondo')
PROPORCIONALES = ('ordinario', 'extraordinario', 'fondo')
CENTAVO = Decimal('0.01')
NOMBRES = {'convenio': 'cuota de convenio', 'ordinario': 'ordinarias', 'extraordinario': 'extraordinarias',
           'fondo': 'fondo de reserva'}


def con_nombre(montos):
    """[(nombre, monto)] de las partes que no están en cero, para mostrar el desglose."""
    return [(NOMBRES[parte], montos[parte]) for parte in COMPONENTES if montos.get(parte)]


def montos_del_cupon(monto_total, monto_extraordinario, monto_fondo_reserva, monto_convenio):
    """Cuánto le corresponde a cada parte; lo que no es extraordinario, fondo ni convenio es ordinario."""
    return {
        'convenio': monto_convenio,
        'ordinario': monto_total - monto_extraordinario - monto_fondo_reserva - monto_convenio,
        'extraordinario': monto_extraordinario,
        'fondo': monto_fondo_reserva,
    }


def repartir_capital(pendiente, monto):
    """
    Reparte `monto` según lo `pendiente` de cada parte. Devuelve [(parte, monto), ...] sin las partes en cero.
    Nunca asigna a una parte más de lo que debe.
    """
    partes = dict.fromkeys(COMPONENTES, Decimal('0'))
    partes['convenio'] = min(monto, max(pendiente['convenio'], Decimal('0')))
    restante = monto - partes['convenio']

    con_deuda = [parte for parte in PROPORCIONALES if pendiente[parte] > 0]
    total = sum((pendiente[parte] for parte in con_deuda), Decimal('0'))
    a_repartir = min(restante, total)
    if a_repartir > 0:
        for parte in con_deuda[:-1]:
            partes[parte] = min((a_repartir * pendiente[parte] / total).quantize(CENTAVO, rounding=ROUND_HALF_UP),
                                pendiente[parte])
        ultima = con_deuda[-1]
        partes[ultima] = a_repartir - sum((partes[parte] for parte in con_deuda[:-1]), Decimal('0'))
        # Si por redondeo la última quedó pasada, el centavo va a la primera parte que todavía debe.
        sobrante = partes[ultima] - pendiente[ultima]
        if sobrante > 0:
            partes[ultima] = pendiente[ultima]
            for parte in con_deuda:
                lugar = min(sobrante, pendiente[parte] - partes[parte])
                partes[parte] += lugar
                sobrante -= lugar
    return [(parte, partes[parte]) for parte in COMPONENTES if partes[parte] > 0]
