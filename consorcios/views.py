from config.views import *
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.decorators import method_decorator
from .tables import *
from .models import *
from .forms import *

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('consorcios.view_consorcio', raise_exception=True), name='dispatch')
class ListarConsorcios(Lista):
    model = Consorcio
    table_class = TablaConsorcios
    export_name = 'consorcios'
    filterset_class = FiltroConsorcios
    template_name = 'listar_consorcios.html'
    acciones = [
        { "nombre": "Crear", "tipo": "link", "perm": "consorcios.add_consorcio", "url": "crear_consorcio" },
    ]
    columnas_con_permiso = {} # dict
    columnas_a_ocultar = {} # set

@login_required
@permission_required('consorcios.change_consorcio', raise_exception=True)
def gestionar_consorcio(request, id):
    """
    Vista para gestionar un consorcio.
    Permite ver y editar los datos del consorcio.

    :param request: Objeto HttpRequest.
    :param id: ID del consorcio a gestionar.
    :return: Renderiza la plantilla de gestión de consorcios.
    """

    consorcio = Consorcio.objects.get(id=id)
    if request.method == 'POST':
        # Aquí se procesaría el formulario de edición del consorcio
        pass

    return render(request, 'gestionar_consorcio.html', {'consorcio': consorcio})


def crear_consorcio(request):
    """
    Vista para crear un nuevo consorcio.
    Permite ingresar los datos del consorcio y guardarlos en la base de datos.

    :param request: Objeto HttpRequest.
    :return: Renderiza la plantilla de creación de consorcios.
    """
    
    return crear_modelo(
        request=request,
        formulario_modelo=FormularioConsorcio,
        template="crear_consorcio.html",
        vista_exito="listar_consorcios",
    ) 
