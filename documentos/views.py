from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from consorcios.models import Consorcio
from gastos.views import consorcios_permitidos
from usuarios.models import Propietario

from .forms import FormularioDocumento
from .models import DocumentoConsorcio


@login_required
@permission_required('consorcios.view_consorcio', raise_exception=True)
def documentos_consorcio(request):
    """El administrador sube y borra los documentos de cada consorcio que administra."""
    consorcios = consorcios_permitidos(request.user).order_by('nombre')
    consorcio_id = request.GET.get('consorcio') or request.POST.get('consorcio') or ''
    consorcio = consorcios.filter(pk=consorcio_id).first() if consorcio_id.isdecimal() else None
    consorcio = consorcio or consorcios.first()
    formulario = FormularioDocumento(request.POST or None, request.FILES or None)
    if request.method == 'POST' and consorcio and formulario.is_valid():
        documento = formulario.save(commit=False)
        documento.consorcio = consorcio
        documento.save()
        messages.success(request, f'Documento "{documento.titulo}" subido.')
        return redirect(f"{request.path}?consorcio={consorcio.pk}")
    return render(request, 'documentos_consorcio.html', {
        'consorcios': consorcios, 'consorcio': consorcio, 'formulario': formulario,
        'documentos': consorcio.documentos.all() if consorcio else [],
    })


@login_required
@permission_required('consorcios.view_consorcio', raise_exception=True)
@require_POST
def borrar_documento(request, documento_id):
    documento = get_object_or_404(
        DocumentoConsorcio, pk=documento_id, consorcio__in=consorcios_permitidos(request.user)
    )
    documento.archivo.delete(save=False)
    documento.delete()
    messages.success(request, 'Documento borrado.')
    return redirect(f"{reverse('documentos_consorcio')}?consorcio={documento.consorcio_id}")


@login_required
def mis_documentos(request):
    """Documentos de los consorcios donde el propietario tiene alguna UF, agrupados por consorcio."""
    propietario = get_object_or_404(Propietario, usuario=request.user)
    consorcios = Consorcio.objects.filter(
        unidades_funcionales__propietario=propietario
    ).distinct().order_by('nombre').prefetch_related('documentos')
    return render(request, 'mis_documentos.html', {'consorcios': consorcios})
