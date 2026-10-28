from consorcios.models import UnidadFuncional
from usuarios.models import Propietario

from .models import ConvenioPago
from .notificaciones import contexto_notificaciones_propietario


def notificaciones(request):
    """Agrega notificaciones de liquidaciones al encabezado global de la sidebar."""
    contexto_vacio = {
        'notificaciones_propietario': [],
        'notificaciones_propietario_total': 0,
        'tiene_convenio': False,
        'unidades_propietario': [],
        'unidad_activa': None,
    }
    usuario = getattr(request, 'user', None)
    if not usuario or not usuario.is_authenticated:
        return contexto_vacio

    propietario = Propietario.objects.filter(usuario_id=usuario.pk).first()
    if propietario is None:
        return contexto_vacio

    contexto = contexto_notificaciones_propietario(propietario)
    # Convenios vigentes o caídos: los cumplidos ya no hace falta mostrarlos.
    contexto['tiene_convenio'] = ConvenioPago.objects.filter(
        unidad_funcional__propietario=propietario, estado__in=['vigente', 'caido'],
    ).exists()
    # Unidad activa del portal: la elegida en el selector del sidebar (o la primera).
    unidades = list(UnidadFuncional.objects.filter(propietario=propietario).select_related('consorcio').order_by(
        'consorcio__nombre', 'piso', 'departamento'))
    elegida = request.session.get('unidad_propietario')
    contexto['unidades_propietario'] = unidades
    contexto['unidad_activa'] = next((u for u in unidades if u.pk == elegida), unidades[0] if unidades else None)
    return contexto
