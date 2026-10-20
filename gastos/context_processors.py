from usuarios.models import Propietario

from .notificaciones import contexto_notificaciones_propietario


def notificaciones(request):
    """Agrega notificaciones de liquidaciones al encabezado global de la sidebar."""
    contexto_vacio = {
        'notificaciones_propietario': [],
        'notificaciones_propietario_total': 0,
    }
    usuario = getattr(request, 'user', None)
    if not usuario or not usuario.is_authenticated:
        return contexto_vacio

    propietario = Propietario.objects.filter(usuario_id=usuario.pk).first()
    if propietario is None:
        return contexto_vacio

    return contexto_notificaciones_propietario(propietario)
