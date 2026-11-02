from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import number_format

from consorcios.models import UnidadFuncional

from .models import NotificacionLiquidacion, Novedad

ETIQUETAS = dict(Novedad.TIPOS, liquidacion='Liquidación')


def avisar_consorcio(consorcio, tipo, texto, url=''):
    """Una novedad para cada propietario con unidad en el consorcio (una sola aunque tenga varias)."""
    propietarios = UnidadFuncional.objects.filter(
        consorcio=consorcio, propietario__isnull=False,
    ).values_list('propietario_id', flat=True).distinct()
    return Novedad.objects.bulk_create([
        Novedad(propietario_id=propietario_id, consorcio=consorcio, tipo=tipo, texto=texto, url=url)
        for propietario_id in propietarios
    ])


def avisar_unidad(unidad, tipo, texto, detalle='', url=''):
    """Novedad para el propietario de una unidad puntual (pagos, consultas)."""
    if not unidad.propietario_id:
        return None
    return Novedad.objects.create(
        propietario_id=unidad.propietario_id, consorcio_id=unidad.consorcio_id, unidad_funcional=unidad,
        tipo=tipo, texto=texto, detalle=detalle, url=url,
    )


def cuando(momento, ahora=None):
    """'hace 5 min', 'hace 2 h', 'ayer' o la fecha corta."""
    ahora = ahora or timezone.now()
    segundos = (ahora - momento).total_seconds()
    if segundos < 3600:
        return f'hace {max(1, int(segundos // 60))} min'
    dia, hoy = timezone.localdate(momento), timezone.localdate(ahora)
    if dia == hoy:
        return f'hace {int(segundos // 3600)} h'
    if (hoy - dia).days == 1:
        return 'ayer'
    return dia.strftime('%d/%m')


def _item_liquidacion(notificacion):
    from .views import periodo_legible

    detalle = notificacion.detalle_liquidacion
    return {
        'tipo': 'liquidacion',
        'etiqueta': ETIQUETAS['liquidacion'],
        'texto': f'Nueva liquidación: {periodo_legible(detalle.liquidacion.periodo)}',
        'detalle': f'Te corresponde $ {number_format(detalle.monto_total, 2, force_grouping=True)}',
        'creada': notificacion.creada,
        'leida': notificacion.leida_en is not None,
        'url': reverse('abrir_notificacion_liquidacion', args=[notificacion.pk]),
    }


def _item_novedad(novedad):
    return {
        'tipo': novedad.tipo,
        'etiqueta': ETIQUETAS[novedad.tipo],
        'texto': novedad.texto,
        'detalle': novedad.detalle,
        'creada': novedad.creada,
        'leida': novedad.leida_en is not None,
        'url': reverse('abrir_novedad', args=[novedad.pk]),
    }


def _ordenar(items):
    items.sort(key=lambda item: item['creada'], reverse=True)
    ahora = timezone.now()
    for item in items:
        item['cuando'] = cuando(item['creada'], ahora)
    return items


def novedades_unidad(propietario, unidad, limite=5):
    """Últimas novedades de una unidad para el Inicio: su liquidación, sus pagos y consultas, y lo del edificio."""
    liquidaciones = NotificacionLiquidacion.objects.filter(
        propietario=propietario, detalle_liquidacion__unidad_funcional=unidad,
    ).select_related('detalle_liquidacion__liquidacion')[:limite]
    novedades = Novedad.objects.filter(
        propietario=propietario, consorcio_id=unidad.consorcio_id,
    ).filter(Q(unidad_funcional__isnull=True) | Q(unidad_funcional=unidad))[:limite]
    items = [_item_liquidacion(n) for n in liquidaciones] + [_item_novedad(n) for n in novedades]
    return _ordenar(items)[:limite]


def contexto_notificaciones_propietario(propietario):
    """Lo no leído de todas sus unidades, para la campanita."""
    liquidaciones = NotificacionLiquidacion.objects.filter(
        propietario=propietario, leida_en__isnull=True,
    ).select_related('detalle_liquidacion__liquidacion')
    novedades = Novedad.objects.filter(propietario=propietario, leida_en__isnull=True)
    items = _ordenar([_item_liquidacion(n) for n in liquidaciones] + [_item_novedad(n) for n in novedades])
    return {
        'mostrar_notificaciones_propietario': True,
        'notificaciones_propietario': items,
        'notificaciones_propietario_total': len(items),
    }
