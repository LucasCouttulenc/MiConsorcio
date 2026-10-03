import os
from django import template
register = template.Library()

@register.filter
def obtener_nombre(valor):
    return valor._meta.verbose_name

@register.filter
def obtener_nombre_en_plural(valor):
    return valor._meta.verbose_name_plural


@register.filter
def get_item(diccionario, clave):
    """Devuelve diccionario[clave] o None si no existe."""
    if not diccionario:
        return None
    return diccionario.get(clave)


@register.filter
def dict_get_tupla(diccionario, args):
    """
    Igual que get_item, pero recibe 'a,b' y busca la clave (int(a), int(b)).
    Sirve para indexar el dict `actuales` con claves (uf_id, grupo_id).
    """
    if not diccionario:
        return None
    try:
        a, b = args.split(',')
        return diccionario.get((int(a), int(b)))
    except (ValueError, AttributeError):
        return None


@register.filter
def basename(valor):
    """Nombre del archivo sin la ruta (comprobantes/2026/10/x.pdf -> x.pdf)."""
    return os.path.basename(str(valor))
