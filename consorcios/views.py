from config.views import *
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.decorators import method_decorator
from usuarios.models import Administrador
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

    def get_queryset(self):
        """
        Obtiene el queryset de consorcios según el usuario autenticado.
        """
        usuario = self.request.user
        queryset = super().get_queryset()
        if usuario.is_superuser:
            return queryset
        else:
            administrador = Administrador.objects.filter(usuario=usuario).first()
            consorcios = administrador.consorcios.all() if administrador else Consorcio.objects.none()
            return queryset.filter(id__in=consorcios)

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

    return gestionar_modelo(
        request=request,
        id_modelo=id,
        formulario_modelo=FormularioConsorcio,
        template="gestionar_consorcio.html",
    )

@login_required
@permission_required('consorcios.add_consorcio', raise_exception=True)
def crear_consorcio(request):
    """
    Vista para crear un nuevo consorcio.
    Permite ingresar los datos del consorcio y guardarlos en la base de datos.

    :param request: Objeto HttpRequest.
    :return: Renderiza la plantilla de creación de consorcios.
    """

    """Agrega el consocio al administrador que lo crea, si es que no es superusuario."""
    def func_post_save(modelo, _form):
        if request.user.is_superuser: return

        administrador = Administrador.objects.filter(usuario=request.user).first()
        if administrador:
            administrador.consorcios.add(modelo)
            administrador.save()

    return crear_modelo(
        request=request,
        formulario_modelo=FormularioConsorcio,
        template="crear_consorcio.html",
        vista_exito="listar_consorcios",
        func_post_save=func_post_save
    ) 

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('consorcios.view_unidadfuncional', raise_exception=True), name='dispatch')
class ListarUnidadesFuncionales(Lista):
    model = UnidadFuncional
    table_class = TablaUnidadesFuncionales
    export_name = 'unidades_funcionales'
    filterset_class = FiltroUnidadesFuncionales
    template_name = 'listar_unidades_funcionales.html'
    acciones = [
        { "nombre": "Crear", "tipo": "link", "perm": "consorcios.add_unidadfuncional", "url": "crear_unidad_funcional"},
    ]
    columnas_con_permiso = {} # dict
    columnas_a_ocultar = {} # set

    def get_queryset(self):
        """
        Obtiene el queryset de unidades funcionales según el consorcio deseado y el usuario autenticado.
        """
        usuario = self.request.user
        consorcio_id = self.kwargs.get('consorcio_id')
        queryset = super().get_queryset()    

        if usuario.is_superuser:
            return queryset

        # Si es administrador de este consorcio
        administrador = Administrador.objects.filter(usuario=usuario).first()
        if administrador and administrador.administra(consorcio_id):
            return queryset.filter(consorcio_id=consorcio_id)

        messages.error(self.request, "No tenes permisos para ver las unidades funcionales de este consorcio.")
        return queryset.none()

    def get_context_data(self, **kwargs):
        """
        Agrega el consorcio al contexto para poder mostrar su nombre en la plantilla.
        """
        context = super().get_context_data(**kwargs)
        consorcio_id = self.kwargs.get('consorcio_id')
        consorcio = Consorcio.objects.filter(id=consorcio_id).first()
        context['consorcio'] = consorcio
        context['elemento'] = consorcio
        return context

@login_required
@permission_required('consorcios.add_unidadfuncional', raise_exception=True)
def crear_unidad_funcional(request, consorcio_id):
    """
    Vista para crear una nueva unidad funcional dentro de un consorcio específico.

    :param request: Objeto HttpRequest.
    :param consorcio_id: ID del consorcio al que pertenece la unidad funcional.
    """

    usuario = request.user
    administrador = Administrador.objects.filter(usuario=usuario).first()
    if not usuario.is_superuser and not administrador.administra(consorcio_id):
        messages.error(request, "No tenes permisos para crear una unidad funcional en este consorcio.")
        return redirect('listar_unidades_funcionales', consorcio_id=consorcio_id)

    consorcio = Consorcio.objects.filter(id=consorcio_id).first()

    return crear_modelo(
        request=request,
        formulario_modelo=FormularioUnidadFuncional,
        template="crear_unidad_funcional.html",
        vista_exito="listar_unidades_funcionales",
        params_vista_exito={"consorcio_id": consorcio_id},
        modelo_secundario=consorcio
    )