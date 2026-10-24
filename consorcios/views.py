from config.views import *
from config.comun import GRUPO_ADMINISTRADORES
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.decorators import method_decorator
from usuarios.models import Administrador
from .tables import *
from .models import *
from .forms import *
from decimal import Decimal
from django.contrib import messages
from django.db import transaction
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404
from django.urls import reverse
import re
from .alicuotas import leer_alicuotas, guardar_alicuotas, suma_alicuotas, consorcio_tiene_alicuotas_validas


def _administra(usuario, consorcio_id):
    """
    Indica si el usuario puede gestionar el consorcio: es superusuario o es su administrador.
    Contempla usuarios con permisos pero sin registro de Administrador.
    """
    if usuario.is_superuser:
        return True
    administrador = Administrador.objects.filter(usuario=usuario).first()
    return bool(administrador and administrador.administra(consorcio_id))

@login_required
@permission_required('consorcios.change_consorcio', raise_exception=True)
def gestionar_consorcio(request):
    """
    Vista para gestionar los datos del consorcio activo (sin pedir ID por URL).
    """
    consorcio_id = request.session.get('consorcio_activo_id')
    if not consorcio_id:
        messages.error(request, "Seleccioná un consorcio primero.")
        return redirect('bienvenida')

    if not _administra(request.user, consorcio_id):
        messages.error(request, "No tenes permisos para gestionar este consorcio.")
        return redirect('bienvenida')

    return gestionar_modelo(
        request=request,
        id_modelo=consorcio_id,
        formulario_modelo=FormularioConsorcio,
        template="gestionar_consorcio.html",
    )

@login_required
@permission_required('consorcios.add_consorcio', raise_exception=True)
def crear_consorcio(request):
    """
    Vista para crear un nuevo consorcio.
    Al crearlo, lo dejamos seleccionado en la sesión automáticamente
    y le creamos una estructura base (Rubro y Columna) para que sea usable.
    """
    def func_post_save(modelo, _form):
        # Lo seleccionamos como activo
        request.session['consorcio_activo_id'] = modelo.id
        
        # Si no es superusuario, lo asignamos a su perfil
        if not request.user.is_superuser:
            administrador = Administrador.objects.filter(usuario=request.user).first()
            if administrador:
                administrador.consorcios.add(modelo)
                administrador.save()

        # --- AUTO-CREACIÓN DE ESTRUCTURA BASE ---
        # Creamos un rubro por defecto
        rubro, _ = Rubro.objects.get_or_create(
            consorcio=modelo, 
            nombre='GASTOS GENERALES'
        )
        # Creamos una columna General por defecto
        GrupoProrrateo.objects.get_or_create(
            consorcio=modelo, 
            rubro=rubro, 
            codigo='A', 
            defaults={
                'nombre': 'General', 
                'tipo_reparto': TipoReparto.GENERAL
            }
        )

    return crear_modelo(
        request=request,
        formulario_modelo=FormularioConsorcio,
        template="crear_consorcio.html",
        vista_exito="gestionar_consorcio",
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
    
    # agregaremos manualmente o vía contexto
    acciones = [] 
    columnas_con_permiso = {"gestionar": "consorcios.change_unidadfuncional"}
    columnas_a_ocultar = {}

    def get_queryset(self):
        queryset = super().get_queryset()
        consorcio_id = self.request.session.get('consorcio_activo_id')
        
        if not consorcio_id:
            return queryset.none()
            
        return queryset.filter(consorcio_id=consorcio_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        consorcio_id = self.request.session.get('consorcio_activo_id')
        
        if consorcio_id:
            consorcio = Consorcio.objects.filter(id=consorcio_id).first()
            context['consorcio'] = consorcio
            # context['elemento'] = consorcio  <-- ELIMINAR ESTA LÍNEA
            
            context['acciones'] = [
                { "nombre": "Crear Unidad Funcional", "label": "Crear Unidad Funcional", "tipo": "link", "url": "crear_unidad_funcional" },
                { "nombre": "Cambiar porcentajes", "label": "Cambiar porcentajes", "tipo": "link", "url": "definir_alicuotas" }
            ]
        return context

@login_required
@permission_required('consorcios.add_unidadfuncional', raise_exception=True)
def crear_unidad_funcional(request, consorcio_id=None):
    """
    Vista para crear una nueva unidad funcional.
    """
    if consorcio_id is not None and not _administra(request.user, consorcio_id):
        messages.error(request, "No tenes permisos para crear una unidad funcional en este consorcio.")
        return redirect('bienvenida')


    vista_exito = "listar_unidades_funcionales"
    params_vista_exito = None
    
    # Si venimos desde un consorcio, forzamos la ida a alícuotas al terminar
    consorcio_obj = None
    if consorcio_id:
        consorcio_obj = Consorcio.objects.filter(id=consorcio_id).first()
        vista_exito = "definir_alicuotas"
        params_vista_exito = {"consorcio_id": consorcio_id}

    # Le pasamos el consorcio al formulario, o el usuario si es una creación general
    modelo_sec = consorcio_obj if consorcio_obj else request.user

    return crear_modelo(
        request=request,
        formulario_modelo=FormularioUnidadFuncional,
        template="crear_unidad_funcional.html",
        vista_exito=vista_exito,
        params_vista_exito=params_vista_exito,
        modelo_secundario=modelo_sec
    )
@login_required
@permission_required('consorcios.change_unidadfuncional', raise_exception=True)
def gestionar_unidad_funcional(request, unidad_id):
    """
    Vista para gestionar una unidad funcional específica.
    Permite ver y editar los datos de la unidad funcional.

    :param request: Objeto HttpRequest.
    :param id: ID de la unidad funcional a gestionar.
    :return: Renderiza la plantilla de gestión de unidades funcionales.
    """

    unidad_funcional = get_object_or_404(UnidadFuncional, id=unidad_id)
    if not _administra(request.user, unidad_funcional.consorcio_id):
        messages.error(request, "No tenes permisos para gestionar esta unidad funcional.")
        return redirect('bienvenida')


    return gestionar_modelo(
        request=request,
        id_modelo=unidad_id,
        formulario_modelo=FormularioUnidadFuncional,
        template="gestionar_unidad_funcional.html",
        modelo_secundario=request.user
    )
    
    
    


@method_decorator(login_required, name='dispatch')
@method_decorator(permission_required('consorcios.view_personal', raise_exception=True), name='dispatch')
class ListarPersonal(Lista):
    model = Personal
    table_class = TablaPersonal
    export_name = 'personal'
    filterset_class = FiltroPersonal
    template_name = 'listar_personal.html'
    acciones = [] # Lo manejamos en get_context_data
    columnas_con_permiso = {"gestionar": "consorcios.change_personal"}
    columnas_a_ocultar = {}

    def get_queryset(self):
        queryset = super().get_queryset()
        consorcio_id = self.request.session.get('consorcio_activo_id')
        
        if not consorcio_id:
            return queryset.none()
            
        return queryset.filter(consorcio_id=consorcio_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        consorcio_id = self.request.session.get('consorcio_activo_id')
        
        if consorcio_id:
            consorcio = Consorcio.objects.filter(id=consorcio_id).first()
            context['consorcio'] = consorcio
            
            # Habilitamos el botón de agregar personal
            context['acciones'] = [
                { "nombre": "Agregar", "tipo": "link", "perm": "consorcios.add_personal", "url": "crear_personal"}
            ]
        return context

@login_required
@permission_required('consorcios.add_personal', raise_exception=True)
def crear_personal(request):
    """
    Vista para agregar personal al consorcio activo.
    """
    consorcio_id = request.session.get('consorcio_activo_id')
    
    if not consorcio_id or not _administra(request.user, consorcio_id):
        messages.error(request, "Seleccioná un consorcio válido para agregar personal.")
        return redirect('listar_personal')

    consorcio = get_object_or_404(Consorcio, id=consorcio_id)

    return crear_modelo(
        request=request,
        formulario_modelo=FormularioPersonal,
        template="crear_personal.html",
        vista_exito="listar_personal",
        modelo_secundario=consorcio
    )

@login_required
@permission_required('consorcios.change_personal', raise_exception=True)
def gestionar_personal(request, personal_id):
    """
    Vista para gestionar los datos de un personal específico.

    :param request: Objeto HttpRequest.
    :param personal_id: ID del personal a gestionar.
    :return: Renderiza la plantilla de gestión de personal.
    """

    personal = get_object_or_404(Personal, id=personal_id)
    if not _administra(request.user, personal.consorcio_id):
        messages.error(request, "No tenes permisos para gestionar este personal.")
        return redirect('bienvenida')


    return gestionar_modelo(
        request=request,
        id_modelo=personal_id,
        formulario_modelo=FormularioPersonal,
        template="gestionar_personal.html",
    )


def _consorcio_gestionable(request, consorcio_id):
    """Devuelve el consorcio si el usuario puede gestionarlo, o None si no tiene permiso."""
    consorcio = get_object_or_404(Consorcio, id=consorcio_id)
    if not request.user.is_superuser:
        administrador = Administrador.objects.filter(usuario=request.user).first()
        if not administrador or not administrador.administra(consorcio_id):
            return None
    return consorcio
 
 
 
 
@login_required
@permission_required('consorcios.change_unidadfuncional', raise_exception=True)
def definir_alicuotas(request):
    """
    Pantalla simple: una sola alícuota por UF, la suma debe dar 100%.
    """
    consorcio_id = request.session.get('consorcio_activo_id')
    
    if not consorcio_id:
        messages.error(request, "Seleccioná un consorcio primero.")
        return redirect('bienvenida')

    consorcio = get_object_or_404(Consorcio, id=consorcio_id)

    # Permisos
    if not _administra(request.user, consorcio_id):
        messages.error(request, "No tenés permisos para gestionar este consorcio.")
        return redirect('bienvenida')


    unidades = (
        consorcio.unidades_funcionales
        .select_related('propietario')
        .order_by('piso', 'departamento')
    )

    if request.method == 'POST':
        valores, errores = leer_alicuotas(request.POST, unidades)
        if errores:
            for e in errores:
                messages.error(request, e)
        else:
            guardar_alicuotas(consorcio, valores)
            messages.success(request, "Alícuotas guardadas correctamente.")
            return redirect('definir_alicuotas') # Ya no lleva parámetros

    suma = suma_alicuotas(consorcio)
    return render(request, 'definir_alicuotas.html', {
        'consorcio': consorcio,
        'unidades': unidades,
        'suma': suma,
        'suma_valida': suma == 100,
    })

def _generar_codigo_columna(consorcio, nombre):
    base = re.sub(r'[^A-Za-z0-9]', '', nombre).upper()[:10] or 'COL'
    codigo = base
    i = 1
    while GrupoProrrateo.objects.filter(consorcio=consorcio, codigo=codigo).exists():
        sufijo = str(i)
        codigo = base[:10 - len(sufijo)] + sufijo
        i += 1
    return codigo


@login_required
@permission_required('consorcios.view_consorcio', raise_exception=True)
def configurar_columnas(request):
    """
    Pantalla principal: lista los rubros del consorcio activo.
    """
    consorcio_id = request.session.get('consorcio_activo_id')
    
    if not consorcio_id:
        messages.error(request, "Seleccioná un consorcio primero.")
        return redirect('bienvenida')

    consorcio = get_object_or_404(Consorcio, id=consorcio_id)

    if request.method == 'POST':
        accion = request.POST.get('accion', '')
        try:
            with transaction.atomic():
                if accion == 'crear_rubro':
                    nombre = request.POST.get('nombre_rubro', '').strip()[:100]
                    if not nombre:
                        raise ValueError("Poné un nombre para el rubro.")
                    if Rubro.objects.filter(consorcio=consorcio, nombre__iexact=nombre).exists():
                        raise ValueError(f"Ya existe un rubro '{nombre}' en este consorcio.")
                    rubro = Rubro.objects.create(consorcio=consorcio, nombre=nombre)
                    messages.success(request, f"Rubro '{rubro.nombre}' creado.")

                elif accion == 'editar_rubro':
                    rubro = get_object_or_404(Rubro, pk=request.POST.get('rubro_id', ''), consorcio=consorcio)
                    nombre = request.POST.get('nombre_rubro', '').strip()[:100]
                    if not nombre:
                        raise ValueError("Poné un nombre para el rubro.")
                    if Rubro.objects.filter(consorcio=consorcio, nombre__iexact=nombre).exclude(pk=rubro.pk).exists():
                        raise ValueError(f"Ya existe otro rubro '{nombre}' en este consorcio.")
                    rubro.nombre = nombre
                    rubro.save(update_fields=['nombre'])
                    messages.success(request, f"Rubro actualizado a '{nombre}'.")

                elif accion == 'borrar_rubro':
                    rubro = get_object_or_404(Rubro, pk=request.POST.get('rubro_id', ''), consorcio=consorcio)
                    if rubro.columnas.exists():
                        raise ValueError(
                            f"No se puede borrar '{rubro.nombre}': tiene {rubro.columnas.count()} columna(s). "
                            "Borrá primero las columnas."
                        )
                    nombre = rubro.nombre
                    rubro.delete()
                    messages.success(request, f"Rubro '{nombre}' eliminado.")

        except ValueError as e:
            messages.error(request, str(e))
        return redirect('configurar_columnas')

    rubros = consorcio.rubros.prefetch_related('columnas').order_by('nombre')

    return render(request, 'configurar_columnas.html', {
        'consorcio': consorcio,
        'rubros': rubros,
    })


@login_required
@permission_required('consorcios.view_consorcio', raise_exception=True)
def editar_columnas_rubro(request, rubro_id):
    """
    Pantalla de edición de un rubro específico: sus columnas (crear, editar,
    borrar) con tipo de reparto y UF afectadas.
    """
    rubro = get_object_or_404(Rubro.objects.select_related('consorcio'), pk=rubro_id)
    consorcio = rubro.consorcio

    # Permisos
    if not request.user.is_superuser:
        administrador = Administrador.objects.filter(usuario=request.user).first()
        if not administrador or not administrador.administra(consorcio.id):
            messages.error(request, "No tenés permisos para gestionar este consorcio.")
            return redirect('bienvenida')


    unidades = consorcio.unidades_funcionales.order_by('piso', 'departamento')

    if request.method == 'POST':
        accion = request.POST.get('accion', '')
        try:
            with transaction.atomic():
                if accion == 'borrar':
                    columna = get_object_or_404(
                        GrupoProrrateo,
                        pk=request.POST.get('columna_id', ''),
                        consorcio=consorcio,
                        rubro=rubro,
                    )
                    nombre_col = columna.nombre
                    try:
                        columna.delete()
                        messages.success(request, f"Columna '{nombre_col}' eliminada.")
                    except ProtectedError:
                        messages.error(request, f"No se puede borrar '{nombre_col}': tiene gastos de liquidaciones asociados.")

                elif accion in ('crear', 'editar'):
                    nombre = request.POST.get('nombre', '').strip()[:100]
                    tipo = request.POST.get('tipo_reparto', '')

                    if not nombre:
                        raise ValueError("Poné un nombre para la columna.")
                    if tipo not in TipoReparto.values:
                        raise ValueError("Elegí un tipo de reparto válido.")

                    total_ufs_consorcio = consorcio.unidades_funcionales.count()

                    ufs_ids = request.POST.getlist('unidades')
                    ufs = list(consorcio.unidades_funcionales.filter(id__in=ufs_ids)) if ufs_ids else []
                    if tipo == TipoReparto.PARTICULAR and len(ufs) != 1:
                        raise ValueError("En una columna Particular tenés que elegir exactamente 1 UF que pague.")
                    
                    if tipo == TipoReparto.PARCIAL and len(ufs) == total_ufs_consorcio and total_ufs_consorcio > 0:
                        raise ValueError("En una columna Parcial no podés excluir a todas las UF (para eso usá General).")

                    if accion == 'editar':
                        columna = get_object_or_404(
                            GrupoProrrateo,
                            pk=request.POST.get('columna_id', ''),
                            consorcio=consorcio,
                            rubro=rubro,
                        )
                        columna.nombre = nombre
                        columna.tipo_reparto = tipo
                        columna.save(update_fields=['nombre', 'tipo_reparto'])
                    else:
                        columna = GrupoProrrateo.objects.create(
                            consorcio=consorcio,
                            rubro=rubro,
                            nombre=nombre,
                            tipo_reparto=tipo,
                            codigo=_generar_codigo_columna(consorcio, nombre),
                        )
                    columna.unidades.set(ufs if tipo != TipoReparto.GENERAL else [])
                    messages.success(request, f"Columna '{nombre}' guardada.")

        except (ValueError, ProtectedError) as e:
            messages.error(request, str(e))
        return redirect('editar_columnas_rubro', rubro_id=rubro.pk)

    columnas = rubro.columnas.prefetch_related('unidades').order_by('codigo')

    return render(request, 'editar_columnas_rubro.html', {
        'consorcio': consorcio,
        'rubro': rubro,
        'columnas': columnas,
        'unidades': unidades,
        'tipos': TipoReparto.choices,
    })
