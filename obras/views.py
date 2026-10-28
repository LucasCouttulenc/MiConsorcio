from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST

from config.views import Lista, crear_modelo, gestionar_modelo
from consorcios.permisos import consorcio_activo, consorcios_permitidos

from .forms import FormularioAsignacion, FormularioObra, FormularioProveedor, proveedores_visibles
from .models import AsignacionProveedor, Obra, Proveedor
from .tables import FiltroObras, FiltroProveedores, TablaObras, TablaProveedores


def _obra_permitida(request, obra_id):
    """Obra de un consorcio que el usuario administra (404 si no existe o no es suya)."""
    return get_object_or_404(Obra, pk=obra_id, consorcio__in=consorcios_permitidos(request.user))


#####################################################################
#                               OBRAS                               #
#####################################################################

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('consorcios.change_consorcio', raise_exception=True), name='dispatch')
class ListarObras(Lista):
    model = Obra
    table_class = TablaObras
    export_name = 'obras'
    filterset_class = FiltroObras
    template_name = 'listar_obras.html'

    def get_queryset(self):
        consorcio = consorcio_activo(self.request)
        if not consorcio:
            return Obra.objects.none()
        return super().get_queryset().filter(consorcio=consorcio).prefetch_related('proveedores')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['consorcio'] = consorcio_activo(self.request)
        if context['consorcio']:
            context['acciones'] = [{"nombre": "Registrar", "label": "Registrar obra", "url": "crear_obra"}]
        return context


@login_required
@permission_required('consorcios.change_consorcio', raise_exception=True)
def crear_obra(request):
    consorcio = consorcio_activo(request)
    if not consorcio:
        messages.error(request, "Seleccioná un consorcio primero.")
        return redirect('bienvenida')

    return crear_modelo(
        request=request,
        formulario_modelo=FormularioObra,
        template="crear_obra.html",
        vista_exito="listar_obras",
        modelo_secundario=consorcio,
    )


@login_required
@permission_required('consorcios.change_consorcio', raise_exception=True)
def gestionar_obra(request, obra_id):
    """Edita los datos y el estado de la obra, y muestra sus proveedores asignados."""
    obra = _obra_permitida(request, obra_id)
    return gestionar_modelo(
        request=request,
        id_modelo=obra.pk,
        formulario_modelo=FormularioObra,
        template="gestionar_obra.html",
        contexto_adicional={
            'asignaciones': obra.asignaciones.select_related('proveedor'),
            'formulario_asignacion': FormularioAsignacion(obra=obra, usuario=request.user),
        },
    )


@login_required
@permission_required('consorcios.change_consorcio', raise_exception=True)
@require_POST
def asignar_proveedor(request, obra_id):
    obra = _obra_permitida(request, obra_id)
    formulario = FormularioAsignacion(request.POST, obra=obra, usuario=request.user)
    if formulario.is_valid():
        asignacion = formulario.save()
        messages.success(request, f'{asignacion.proveedor} asignado a la obra.')
    else:
        for errores in formulario.errors.values():
            messages.error(request, errores[0])
    return redirect('gestionar_obra', obra_id=obra.pk)


@login_required
@permission_required('consorcios.change_consorcio', raise_exception=True)
@require_POST
def quitar_asignacion(request, asignacion_id):
    asignacion = get_object_or_404(
        AsignacionProveedor, pk=asignacion_id,
        obra__consorcio__in=consorcios_permitidos(request.user))
    obra_id = asignacion.obra_id
    asignacion.delete()
    messages.success(request, f'{asignacion.proveedor} quitado de la obra.')
    return redirect('gestionar_obra', obra_id=obra_id)


#####################################################################
#                            PROVEEDORES                            #
#####################################################################

@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('consorcios.change_consorcio', raise_exception=True), name='dispatch')
class ListarProveedores(Lista):
    model = Proveedor
    table_class = TablaProveedores
    export_name = 'proveedores'
    filterset_class = FiltroProveedores
    template_name = 'listar_proveedores.html'
    acciones = [{"nombre": "Registrar", "label": "Registrar proveedor", "url": "crear_proveedor"}]

    def get_queryset(self):
        return proveedores_visibles(self.request.user)


@login_required
@permission_required('consorcios.change_consorcio', raise_exception=True)
def crear_proveedor(request):
    return crear_modelo(
        request=request,
        formulario_modelo=FormularioProveedor,
        template="crear_proveedor.html",
        vista_exito="listar_proveedores",
        modelo_secundario=request.user,
    )


@login_required
@permission_required('consorcios.change_consorcio', raise_exception=True)
def gestionar_proveedor(request, proveedor_id):
    proveedor = get_object_or_404(proveedores_visibles(request.user), pk=proveedor_id)
    return gestionar_modelo(
        request=request,
        id_modelo=proveedor.pk,
        formulario_modelo=FormularioProveedor,
        template="gestionar_proveedor.html",
        contexto_adicional={'asignaciones': proveedor.asignaciones.select_related('obra__consorcio')},
    )
