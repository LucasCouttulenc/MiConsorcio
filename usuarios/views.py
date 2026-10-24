from django.shortcuts import render
from .forms import FormularioLogin
from .models import Propietario
from django.shortcuts import redirect
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST


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
def cambiar_consorcio_activo(request):
    # Aceptamos tanto POST (desde el sidebar) como GET (desde los botones de la tabla)
    consorcio_id = request.POST.get('consorcio_id') or request.GET.get('consorcio_id')
    next_url = request.POST.get('next') or request.GET.get('next') or request.META.get('HTTP_REFERER', 'bienvenida')

    if consorcio_id:
        request.session['consorcio_activo_id'] = consorcio_id
        
    return redirect(next_url)
