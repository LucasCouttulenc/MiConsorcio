from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from consorcios.models import UnidadFuncional
from gastos.views import consorcios_permitidos
from usuarios.models import Propietario

from .forms import FormularioConsulta, FormularioMensaje
from .models import Consulta, EstadoConsulta, MensajeConsulta


def consultas_del_propietario(propietario):
    return Consulta.objects.filter(unidad_funcional__propietario=propietario).select_related(
        'unidad_funcional__consorcio'
    )


@login_required
def mis_consultas(request):
    """Consultas y reclamos que el propietario le hizo a la administración."""
    propietario = get_object_or_404(Propietario, usuario=request.user)
    consultas = consultas_del_propietario(propietario).annotate(cantidad_mensajes=Count('mensajes'))
    return render(request, 'mis_consultas.html', {'consultas': consultas})


@login_required
def nueva_consulta(request):
    propietario = get_object_or_404(Propietario, usuario=request.user)
    unidades = UnidadFuncional.objects.filter(propietario=propietario).select_related('consorcio').order_by(
        'consorcio__nombre', 'piso', 'departamento'
    )
    if not unidades.exists():
        messages.info(request, 'Necesitás tener una unidad funcional asignada para enviar consultas.')
        return redirect('mis_consultas')
    formulario = FormularioConsulta(request.POST or None, unidades=unidades, initial={
        'unidad_funcional': request.session.get('unidad_propietario'),
    })
    if request.method == 'POST' and formulario.is_valid():
        with transaction.atomic():
            consulta = formulario.save()
            MensajeConsulta.objects.create(
                consulta=consulta, autor=request.user, texto=formulario.cleaned_data['descripcion'],
            )
        messages.success(request, 'Consulta enviada. Te avisamos acá cuando la administración responda.')
        return redirect('ver_consulta', consulta_id=consulta.pk)
    return render(request, 'nueva_consulta.html', {'formulario': formulario})


@login_required
def ver_consulta(request, consulta_id):
    """Hilo de una consulta para el propietario; puede seguir escribiendo mientras no esté cerrada."""
    propietario = get_object_or_404(Propietario, usuario=request.user)
    consulta = get_object_or_404(consultas_del_propietario(propietario), pk=consulta_id)
    formulario = FormularioMensaje(request.POST or None)
    if request.method == 'POST':
        if consulta.cerrada:
            messages.error(request, 'La consulta está cerrada. Si el problema sigue, abrí una nueva.')
        elif formulario.is_valid():
            MensajeConsulta.objects.create(consulta=consulta, autor=request.user, texto=formulario.cleaned_data['texto'])
            consulta.save(update_fields=['actualizada'])
            return redirect('ver_consulta', consulta_id=consulta.pk)
    return render(request, 'ver_consulta.html', {
        'consulta': consulta, 'mensajes_consulta': consulta.mensajes.select_related('autor'), 'formulario': formulario,
    })


def consultas_administradas(usuario):
    return Consulta.objects.filter(
        unidad_funcional__consorcio__in=consorcios_permitidos(usuario)
    ).select_related('unidad_funcional__consorcio', 'unidad_funcional__propietario__usuario')


@login_required
@permission_required('consorcios.view_consorcio', raise_exception=True)
def bandeja_consultas(request):
    """Bandeja del administrador, filtrada por estado."""
    consultas = consultas_administradas(request.user)
    totales = consultas.aggregate(
        abiertas=Count('pk', filter=Q(estado=EstadoConsulta.ABIERTA)),
        en_curso=Count('pk', filter=Q(estado=EstadoConsulta.EN_CURSO)),
        cerradas=Count('pk', filter=Q(estado=EstadoConsulta.CERRADA)),
    )
    # Por defecto, las que esperan respuesta de la administración.
    estado = request.GET.get('estado', EstadoConsulta.ABIERTA)
    if estado in EstadoConsulta.values:
        consultas = consultas.filter(estado=estado)
    else:
        estado = 'todas'
    return render(request, 'bandeja_consultas.html', {
        'consultas': consultas.annotate(cantidad_mensajes=Count('mensajes')),
        'estado': estado, 'totales': totales,
    })


@login_required
@permission_required('consorcios.view_consorcio', raise_exception=True)
def gestionar_consulta(request, consulta_id):
    """El administrador responde (pasa a En curso) o cierra la consulta."""
    consulta = get_object_or_404(consultas_administradas(request.user), pk=consulta_id)
    formulario = FormularioMensaje(request.POST or None)
    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'cerrar' and not consulta.cerrada:
            consulta.estado = EstadoConsulta.CERRADA
            consulta.save(update_fields=['estado', 'actualizada'])
            messages.success(request, 'Consulta cerrada.')
            return redirect('bandeja_consultas')
        if accion == 'responder' and not consulta.cerrada and formulario.is_valid():
            MensajeConsulta.objects.create(
                consulta=consulta, autor=request.user, de_administracion=True, texto=formulario.cleaned_data['texto'],
            )
            consulta.estado = EstadoConsulta.EN_CURSO
            consulta.save(update_fields=['estado', 'actualizada'])
            return redirect('gestionar_consulta', consulta_id=consulta.pk)
    return render(request, 'gestionar_consulta.html', {
        'consulta': consulta, 'mensajes_consulta': consulta.mensajes.select_related('autor'), 'formulario': formulario,
    })
