from django.shortcuts import render
from .forms import FormularioLogin
from django.shortcuts import redirect
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required

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
    return render(request, 'bienvenida.html')
