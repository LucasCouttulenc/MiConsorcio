from django.shortcuts import render
from .forms import FormularioLogin
from django.shortcuts import redirect
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from .models import Propietario
from gastos.notificaciones import contexto_notificaciones_propietario

def login(request):
    if request.user.is_authenticated:
        return redirect('bienvenida')
    elif request.method == 'POST':
        formulario = FormularioLogin(request=request, data=request.POST)
        if formulario.is_valid():
            usuario = formulario.get_user()
            auth_login(request, usuario)
            return redirect('bienvenida')
    else:
        formulario = FormularioLogin()
    return render(request, 'login.html', {'formulario': formulario})

@login_required
def bienvenida(request):
    propietario = Propietario.objects.filter(usuario=request.user).first()
    contexto = contexto_notificaciones_propietario(propietario) if propietario else {}
    return render(request, 'bienvenida.html', contexto)
