from django import template
register = template.Library()

@register.filter
def obtener_nombre(valor):
    return valor._meta.verbose_name

@register.filter
def obtener_nombre_en_plural(valor):
    return valor._meta.verbose_name_plural
