from django.shortcuts import render
from .forms import FormularioLogin
from .models import Propietario
from django.shortcuts import redirect
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from consorcios.permisos import consorcios_permitidos


def pagina_inicial(usuario):
    """El propietario arranca en su Inicio; el resto, en la bienvenida."""
    if Propietario.objects.filter(usuario=usuario).exists():
        return redirect('inicio_propietario')
    return redirect('bienvenida')

def login(request):
    if request.user.is_authenticated:
        return pagina_inicial(request.user)
    elif request.method == 'POST':
        formulario = FormularioLogin(request=request, data=request.POST)
        if formulario.is_valid():
            usuario = formulario.get_user()
            auth_login(request, usuario)
            return pagina_inicial(usuario)
    else:
        formulario = FormularioLogin()
    return render(request, 'login.html', {'formulario': formulario})

@login_required
def bienvenida(request):
    return render(request, 'bienvenida.html')




@login_required
@require_POST
def cambiar_consorcio_activo(request):
    """Cambia el consorcio activo desde el selector del sidebar, solo a uno que el usuario administre."""
    consorcio_id = request.POST.get('consorcio_id', '')
    consorcio = consorcios_permitidos(request.user).filter(pk=consorcio_id).first() if consorcio_id.isdecimal() else None
    if consorcio:
        request.session['consorcio_activo_id'] = consorcio.pk
    else:
        messages.error(request, "No tenés acceso a ese consorcio.")

    destino = request.POST.get('next') or request.META.get('HTTP_REFERER', '')
    if not url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        destino = 'bienvenida'
    return redirect(destino)
