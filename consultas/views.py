from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from consorcios.models import UnidadFuncional
from consorcios.permisos import consorcio_activo
from usuarios.models import Propietario

from .forms import FormularioConsulta, FormularioMensaje
from .models import Consulta, EstadoConsulta, MensajeConsulta


# ==========================================
# VISTAS DEL PROPIETARIO
# ==========================================

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
    # Algunas pantallas abren la consulta ya armada (ej. "Pedir convenio de pago" desde el Inicio).
    formulario = FormularioConsulta(request.POST or None, unidades=unidades, initial={
        'unidad_funcional': request.GET.get('unidad') or request.session.get('unidad_propietario'),
        'asunto': request.GET.get('asunto', '')[:150],
        'descripcion': request.GET.get('descripcion', '')[:3000],
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


# ==========================================
# VISTAS DEL ADMINISTRADOR (CONSORCIO ACTIVO)
# ==========================================

@login_required
@permission_required('consorcios.view_consorcio', raise_exception=True)
def bandeja_consultas(request):
    """Bandeja del administrador, filtrada por el consorcio activo y por estado."""
    consorcio = consorcio_activo(request)
    if not consorcio:
        messages.error(request, "Seleccioná un consorcio primero.")
        return redirect('bienvenida')

    # Filtramos estrictamente por el consorcio activo (ya validado contra los que administra)
    consultas = Consulta.objects.filter(
        unidad_funcional__consorcio=consorcio
    ).select_related('unidad_funcional__consorcio', 'unidad_funcional__propietario__usuario')

    # Filtro opcional si vienen desde el detalle de una UF
    if request.GET.get('unidad', '').isdecimal():
        consultas = consultas.filter(unidad_funcional_id=request.GET['unidad'])

    totales = consultas.aggregate(
        abiertas=Count('pk', filter=Q(estado=EstadoConsulta.ABIERTA)),
        en_curso=Count('pk', filter=Q(estado=EstadoConsulta.EN_CURSO)),
        cerradas=Count('pk', filter=Q(estado=EstadoConsulta.CERRADA)),
    )
    
    # Por defecto, mostramos las que esperan respuesta
    estado = request.GET.get('estado', EstadoConsulta.ABIERTA)
    if estado in EstadoConsulta.values:
        consultas = consultas.filter(estado=estado)
    else:
        estado = 'todas'
        
    return render(request, 'bandeja_consultas.html', {
        'consultas': consultas.annotate(cantidad_mensajes=Count('mensajes')),
        'estado': estado, 
        'totales': totales,
    })


@login_required
@permission_required('consorcios.view_consorcio', raise_exception=True)
def gestionar_consulta(request, consulta_id):
    """El administrador responde (pasa a En curso) o cierra la consulta."""
    consorcio = consorcio_activo(request)
    if not consorcio:
        return redirect('bienvenida')

    # Seguridad: Verificamos que la consulta pertenezca al consorcio activo
    consulta = get_object_or_404(
        Consulta.objects.select_related('unidad_funcional__consorcio', 'unidad_funcional__propietario__usuario'),
        pk=consulta_id,
        unidad_funcional__consorcio=consorcio
    )
    
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
        'consulta': consulta, 
        'mensajes_consulta': consulta.mensajes.select_related('autor'), 
        'formulario': formulario,
    })
