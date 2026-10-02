# consorcios/alicuotas.py
"""Lectura, validación y chequeo de alícuotas de un consorcio."""
from decimal import Decimal, InvalidOperation

TOTAL = Decimal('100')
PASO = Decimal('0.0001')


def nombre_campo(uf_id):
    return f'alicuota_{uf_id}'


def leer_alicuotas(post, unidades):
    """
    Lee las alícuotas del POST y devuelve (valores, errores).

    valores: {uf_id: Decimal}
    Valida que cada uno esté entre 0 y 100, con hasta 4 decimales,
    y que la suma total sea exactamente 100.
    """
    valores, errores = {}, []

    for uf in unidades:
        crudo = (post.get(nombre_campo(uf.pk)) or '').strip().replace(',', '.')
        etiqueta = f'UF {uf.piso}° {uf.departamento or ""}'.strip()

        if crudo == '':
            errores.append(f'{etiqueta}: ingresá un valor.')
            continue

        try:
            valor = Decimal(crudo)
        except InvalidOperation:
            errores.append(f'{etiqueta}: "{crudo}" no es un número válido.')
            continue

        if not valor.is_finite() or valor < 0 or valor > 100:
            errores.append(f'{etiqueta}: la alícuota debe estar entre 0 y 100.')
            continue

        if valor != valor.quantize(PASO):
            errores.append(f'{etiqueta}: usá hasta 4 decimales.')
            continue

        valores[uf.pk] = valor.quantize(PASO)

    if not errores:
        suma = sum(valores.values(), Decimal('0'))
        if suma != TOTAL:
            errores.append(f'La suma de las alícuotas es {suma}% y debe ser exactamente 100%.')

    return valores, errores


def guardar_alicuotas(consorcio, valores):
    """Actualiza UnidadFuncional.alicuota para cada UF en `valores`."""
    from .models import UnidadFuncional
    for uf_id, porcentaje in valores.items():
        UnidadFuncional.objects.filter(pk=uf_id, consorcio=consorcio).update(alicuota=porcentaje)


def suma_alicuotas(consorcio):
    """Devuelve la suma actual de alícuotas del consorcio."""
    from django.db.models import Sum
    from .models import UnidadFuncional
    return UnidadFuncional.objects.filter(consorcio=consorcio).aggregate(
        total=Sum('alicuota')
    )['total'] or Decimal('0')


def consorcio_tiene_alicuotas_validas(consorcio):
    """True si las alícuotas del consorcio suman exactamente 100%."""
    return suma_alicuotas(consorcio) == TOTAL