from consorcios.permisos import consorcios_permitidos, consorcio_activo

def consorcio_context(request):
    if not request.user.is_authenticated:
        return {}

    # Consorcios que el usuario puede ver y el activo (validado contra esos mismos consorcios)
    return {
        'consorcios_disponibles': consorcios_permitidos(request.user).order_by('nombre'),
        'consorcio_activo': consorcio_activo(request),
    }
