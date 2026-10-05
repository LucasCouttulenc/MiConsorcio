from config.views import *
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
    administrador = Administrador.objects.filter(usuario=request.user).first()
    if not request.user.is_superuser and not administrador.administra(id):
        messages.error(request, "No tenes permisos para gestionar este consorcio.")
        return redirect('listar_consorcios')

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
    columnas_con_permiso = {"gestionar": "consorcios.change_unidadfuncional"} # dict
    columnas_a_ocultar = {} # set

    def get_queryset(self):
        """
        Obtiene el queryset de unidades funcionales según el consorcio deseado y el usuario autenticado.
        """
        usuario = self.request.user
        consorcio_id = self.kwargs.get('consorcio_id')
        queryset = super().get_queryset()

        # Si es administrador de este consorcio
        administrador = Administrador.objects.filter(usuario=usuario).first()
        if (administrador and administrador.administra(consorcio_id)) or usuario.is_superuser:
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
        return redirect('listar_consorcios')

    consorcio = Consorcio.objects.filter(id=consorcio_id).first()

    return crear_modelo(
        request=request,
        formulario_modelo=FormularioUnidadFuncional,
        template="crear_unidad_funcional.html",
        vista_exito="listar_unidades_funcionales",
        params_vista_exito={"consorcio_id": consorcio_id},
        modelo_secundario=consorcio
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

    unidad_funcional = UnidadFuncional.objects.filter(id=unidad_id).first()
    consorcio_id = unidad_funcional.consorcio.id
    administrador = Administrador.objects.filter(usuario=request.user).first()
    if not request.user.is_superuser and not administrador.administra(consorcio_id):
        messages.error(request, "No tenes permisos para gestionar esta unidad funcional.")
        return redirect('listar_consorcios')

    return gestionar_modelo(
        request=request,
        id_modelo=unidad_id,
        formulario_modelo=FormularioUnidadFuncional,
        template="gestionar_unidad_funcional.html",
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
def definir_alicuotas(request, consorcio_id):
    """
    Pantalla simple: una sola alícuota por UF, la suma debe dar 100%.
    """
    consorcio = get_object_or_404(Consorcio, id=consorcio_id)

    # Permisos
    administrador = Administrador.objects.filter(usuario=request.user).first()
    if not request.user.is_superuser and not administrador.administra(consorcio_id):
        messages.error(request, "No tenés permisos para gestionar este consorcio.")
        return redirect('listar_consorcios')

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
            return redirect('definir_alicuotas', consorcio_id=consorcio_id)

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
    if request.user.is_superuser:
        consorcios_disp = Consorcio.objects.all().order_by('nombre')
    else:
        consorcios_disp = Consorcio.objects.filter(administradores__usuario=request.user).distinct().order_by('nombre')

    consorcio_id = request.POST.get('consorcio') or request.GET.get('consorcio', '')
    consorcio = consorcios_disp.filter(id=consorcio_id).first() if consorcio_id else None
    if consorcio_id and not consorcio:
        messages.error(request, "No tenés acceso a ese consorcio.")
        return redirect('configurar_columnas')

    if request.method == 'POST' and consorcio:
        accion = request.POST.get('accion', '')
        try:
            with transaction.atomic():
                if accion == 'borrar':
                    columna = get_object_or_404(GrupoProrrateo, pk=request.POST.get('columna_id', ''), consorcio=consorcio)
                    nombre_col = columna.nombre
                    try:
                        columna.delete()
                        messages.success(request, f"Columna '{nombre_col}' eliminada.")
                    except ProtectedError:
                        messages.error(request, f"No se puede borrar '{nombre_col}': tiene gastos de liquidaciones asociados.")
                else:
                    nombre = request.POST.get('nombre', '').strip()[:100]
                    tipo = request.POST.get('tipo_reparto', '')
                    if not nombre:
                        raise ValueError("Poné un nombre para la columna.")
                    if tipo not in TipoReparto.values:
                        raise ValueError("Elegí un tipo de reparto válido.")
                    ufs_ids = request.POST.getlist('unidades')
                    ufs = list(consorcio.unidades_funcionales.filter(id__in=ufs_ids)) if ufs_ids else []
                    if tipo == TipoReparto.PARTICULAR and not ufs:
                        raise ValueError("En una columna Particular elegí al menos una UF que pague.")
                    if accion == 'editar':
                        columna = get_object_or_404(GrupoProrrateo, pk=request.POST.get('columna_id', ''), consorcio=consorcio)
                        columna.nombre = nombre
                        columna.tipo_reparto = tipo
                        columna.save(update_fields=['nombre', 'tipo_reparto'])
                    else:
                        columna = GrupoProrrateo.objects.create(
                            consorcio=consorcio, nombre=nombre, tipo_reparto=tipo,
                            codigo=_generar_codigo_columna(consorcio, nombre))
                    columna.unidades.set(ufs if tipo != TipoReparto.GENERAL else [])
                    messages.success(request, f"Columna '{nombre}' guardada.")
        except ValueError as e:
            messages.error(request, str(e))
        return redirect(f"{reverse('configurar_columnas')}?consorcio={consorcio.id}")

    columnas, unidades = [], []
    if consorcio:
        columnas = consorcio.grupos_prorrateo.prefetch_related('unidades').order_by('nombre')
        unidades = consorcio.unidades_funcionales.order_by('piso', 'departamento')

    return render(request, 'configurar_columnas.html', {
        'consorcios': consorcios_disp,
        'consorcio': consorcio,
        'columnas': columnas,
        'unidades': unidades,
        'tipos': TipoReparto.choices,
    })
