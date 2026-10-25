from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from consorcios.models import Consorcio
from consorcios.permisos import consorcio_activo
from usuarios.models import Propietario

from .forms import FormularioDocumento
from .models import DocumentoConsorcio


@login_required
@permission_required('consorcios.view_consorcio', raise_exception=True)
def documentos_consorcio(request):
    """El administrador sube y borra los documentos del consorcio activo."""
    consorcio = consorcio_activo(request)
    if not consorcio:
        messages.error(request, "Seleccioná un consorcio primero.")
        return redirect('bienvenida')

    formulario = FormularioDocumento(request.POST or None, request.FILES or None)
    
    if request.method == 'POST' and formulario.is_valid():
        documento = formulario.save(commit=False)
        documento.consorcio = consorcio
        documento.save()
        messages.success(request, f'Documento "{documento.titulo}" subido.')
        return redirect('documentos_consorcio')
        
    return render(request, 'documentos_consorcio.html', {
        'consorcio': consorcio,
        'formulario': formulario,
        'documentos': consorcio.documentos.all(),
    })


@login_required
@permission_required('consorcios.view_consorcio', raise_exception=True)
@require_POST
def borrar_documento(request, documento_id):
    consorcio = consorcio_activo(request)
    if not consorcio:
        return redirect('bienvenida')

    documento = get_object_or_404(
        DocumentoConsorcio, pk=documento_id, consorcio=consorcio
    )
    documento.archivo.delete(save=False)
    documento.delete()
    messages.success(request, 'Documento borrado.')
    return redirect('documentos_consorcio')


@login_required
def mis_documentos(request):
    """Documentos de los consorcios donde el propietario tiene alguna UF, agrupados por consorcio."""
    propietario = get_object_or_404(Propietario, usuario=request.user)
    consorcios = Consorcio.objects.filter(
        unidades_funcionales__propietario=propietario
    ).distinct().order_by('nombre').prefetch_related('documentos')
    return render(request, 'mis_documentos.html', {'consorcios': consorcios})