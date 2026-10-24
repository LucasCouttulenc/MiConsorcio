from consorcios.models import Consorcio
from usuarios.models import Administrador

def consorcio_context(request):
    if not request.user.is_authenticated:
        return {}

    # 1. Obtenemos los consorcios que el usuario puede ver
    if request.user.is_superuser:
        consorcios = Consorcio.objects.all().order_by('nombre')
    else:
        admin = Administrador.objects.filter(usuario=request.user).first()
        consorcios = admin.consorcios.all().order_by('nombre') if admin else Consorcio.objects.none()

    # 2. Buscamos el consorcio activo en la sesión
    consorcio_id = request.session.get('consorcio_activo_id')
    consorcio_activo = consorcios.filter(pk=consorcio_id).first()

    # 3. Si no hay activo pero tiene consorcios, seleccionamos el primero por defecto
    if not consorcio_activo and consorcios.exists():
        consorcio_activo = consorcios.first()
        request.session['consorcio_activo_id'] = consorcio_activo.pk

    return {
        'consorcios_disponibles': consorcios,
        'consorcio_activo': consorcio_activo,
    }