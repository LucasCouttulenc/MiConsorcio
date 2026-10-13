from .models import NotificacionLiquidacion


def contexto_notificaciones_propietario(propietario):
    pendientes = NotificacionLiquidacion.objects.filter(
        propietario=propietario, leida_en__isnull=True
    ).select_related(
        'detalle_liquidacion__liquidacion__consorcio',
        'detalle_liquidacion__unidad_funcional',
    )
    notificaciones = list(pendientes)
    return {
        'mostrar_notificaciones_propietario': True,
        'notificaciones_propietario': notificaciones,
        'notificaciones_propietario_total': len(notificaciones),
    }
