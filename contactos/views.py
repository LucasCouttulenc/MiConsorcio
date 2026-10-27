from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from consorcios.models import Consorcio
from consorcios.permisos import consorcio_activo
from usuarios.models import Propietario

from .forms import FormularioContactoAdministracion, FormularioTelefonoUtil
from .models import ContactoAdministracion, TelefonoUtil


@login_required
@permission_required('consorcios.change_consorcio', raise_exception=True)
def contactos_consorcio(request):
    """El administrador carga sus datos de contacto y los teléfonos útiles del consorcio activo."""
    consorcio = consorcio_activo(request)
    if not consorcio:
        messages.error(request, "Seleccioná un consorcio primero.")
        return redirect('bienvenida')

    contacto, _ = ContactoAdministracion.objects.get_or_create(consorcio=consorcio)
    accion = request.POST.get('accion')
    formulario_contacto = FormularioContactoAdministracion(
        request.POST if accion == 'contacto' else None, instance=contacto, prefix='contacto')
    formulario_telefono = FormularioTelefonoUtil(
        request.POST if accion == 'telefono' else None, prefix='telefono')

    if accion == 'contacto' and formulario_contacto.is_valid():
        formulario_contacto.save()
        messages.success(request, 'Datos de la administración guardados.')
        return redirect('contactos_consorcio')
    if accion == 'telefono' and formulario_telefono.is_valid():
        telefono = formulario_telefono.save(commit=False)
        telefono.consorcio = consorcio
        telefono.save()
        messages.success(request, f'Teléfono "{telefono.nombre}" agregado.')
        return redirect('contactos_consorcio')

    return render(request, 'contactos_consorcio.html', {
        'consorcio': consorcio,
        'formulario_contacto': formulario_contacto,
        'formulario_telefono': formulario_telefono,
        'telefonos': consorcio.telefonos_utiles.all(),
    })


@login_required
@permission_required('consorcios.change_consorcio', raise_exception=True)
@require_POST
def borrar_telefono(request, telefono_id):
    consorcio = consorcio_activo(request)
    if not consorcio:
        return redirect('bienvenida')
    telefono = get_object_or_404(TelefonoUtil, pk=telefono_id, consorcio=consorcio)
    telefono.delete()
    messages.success(request, 'Teléfono borrado.')
    return redirect('contactos_consorcio')


@login_required
def mis_contactos(request):
    """Contacto de la administración y teléfonos útiles de cada consorcio donde el propietario tiene una UF."""
    propietario = get_object_or_404(Propietario, usuario=request.user)
    consorcios = Consorcio.objects.filter(
        unidades_funcionales__propietario=propietario
    ).distinct().order_by('nombre').select_related('contacto_administracion').prefetch_related('telefonos_utiles')
    return render(request, 'mis_contactos.html', {'consorcios': consorcios})
