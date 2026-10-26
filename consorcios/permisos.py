from .models import Consorcio


def consorcios_permitidos(usuario):
    """Consorcios que el usuario puede administrar: todos si es superusuario, si no los que tiene asignados."""
    if usuario.is_superuser:
        return Consorcio.objects.all()
    return Consorcio.objects.filter(administradores__usuario=usuario).distinct()


def consorcio_activo(request):
    """
    Consorcio activo de la sesión, solo si el usuario puede administrarlo.
    Si el de la sesión no es válido, toma el primero que tenga permitido y lo guarda.
    Devuelve None si el usuario no administra ningún consorcio.
    """
    consorcios = consorcios_permitidos(request.user).order_by('nombre')
    consorcio_id = str(request.session.get('consorcio_activo_id', ''))
    consorcio = consorcios.filter(pk=consorcio_id).first() if consorcio_id.isdecimal() else None
    if not consorcio:
        consorcio = consorcios.first()
        if consorcio:
            request.session['consorcio_activo_id'] = consorcio.pk
        else:
            request.session.pop('consorcio_activo_id', None)
    return consorcio
