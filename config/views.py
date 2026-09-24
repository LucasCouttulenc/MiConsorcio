from django_filters.views import FilterView
from django_tables2.views import SingleTableMixin
from django.db import transaction
from django.contrib import messages
from django.urls import reverse
from django.shortcuts import redirect, render, get_object_or_404
from .models import *
from .comun import *

EXITO = "Se ha creado correctamente el {}."
EXITO_CREAR = "Se ha creado correctamente el {}."
EXITO_ACTUALIZAR = "Se ha actualizado correctamente el {}."
ERROR_CREAR = "No se pudo crear el {}. Error: {}"
ERROR_FORMULARIO_INVALIDO = "El formulario no es válido. Errores: {}"
ERROR_ACTUALIZAR = "No se pudo actualizar el {}. Error: {}"

class Lista(ExportMixinCustom, SingleTableMixin, FilterView):
    """
    Clase base para listar un modelo.
    Permite filtrar y exportar los registros del modelo.

    :param model: Modelo a listar.
    :param table_class: Clase de la tabla a utilizar.
    :param template_name: Plantilla a renderizar.
    :param filterset_class: Clase del filtro a utilizar.
    :param table_pagination: Configuración de paginación de la tabla.
    :param export_name: Nombre del archivo a exportar.
    :param permiso_para_exportar: Permiso necesario para exportar.
    :param acciones: Lista de acciones a realizar en la tabla.
    :param columnas_con_permiso: Diccionario de columnas con permisos. Si el usuario no tiene 
                                 permiso, la columna se oculta.
    """
    model = None
    table_class = None
    template_name = None
    filterset_class = None
    table_pagination = {'per_page': FILAS_POR_PAGINA }
    export_name = None
    permiso_para_exportar = None
    acciones = []
    columnas_con_permiso = {}
    columnas_a_ocultar = set()

    def get_table(self, **kwargs):
        """
        Devuelve la tabla a utilizar.
        Si el usuario no tiene permiso para ver una columna que lo requiere, se oculta.

        :param kwargs: Parámetros adicionales para la tabla.
        :return: Tabla configurada con los permisos del usuario.
        :rtype: django_tables2.Table
        """
        table = super().get_table(**kwargs)
        table.request = self.request

        # Si el usuario no tiene permiso para ver una columna, se oculta
        for columna, permiso in self.columnas_con_permiso.items():
            if not self.request.user.has_perm(permiso):
                table.exclude += (columna,)
        
        # Si hay columnas a ocultar, las oculto
        for columna in self.columnas_a_ocultar:
            if columna in table.columns:
                table.columns.hide(columna)

        return table

    def get_context_data(self, **kwargs):
        """
        Devuelve el contexto a utilizar en la plantilla.
        Agrega las acciones que se podrán ejecutar a través de botones que se 
        renderizarán sobre la tabla.

        :param kwargs: Parámetros adicionales para el contexto.
        :return: Contexto a utilizar en la plantilla, incluyendo las acciones.
        :rtype: dict
        """
        context = super().get_context_data(**kwargs)
        context['acciones'] = self.acciones
        # Por heredar de FilterView, context['filter'] tiene un FilterSet generado automáticamente, lo saco si no lo definí explícitamente
        if not self.filterset_class: context['filter'] = None
        return context



def crear_modelo(
    request,
    formulario_modelo,
    template, 
    vista_exito, 
    func_post_save=None,
    modelo_secundario=None,
    nombre_modelo=None,
    contexto_adicional=None,
    params_vista_exito=None
):
    """ 
    Vista general para crear un modelo.
    Si el método de la solicitud es POST, se crea el modelo y se redirige a la vista de éxito.
    Si el método de la solicitud es GET, se renderiza el formulario.
    En caso de error o éxito, se muestran mensajes correspondientes.

    :param request: Objeto HttpRequest.
    :param formulario_modelo: Clase del formulario a utilizar.
    :param template: Plantilla a renderizar.
    :param vista_exito: Vista a la que redirigir después de crear el modelo.
    :param func_post_save: Función a ejecutar después de guardar el modelo.
    :param modelo_secundario: Modelo secundario relacionado. Este se pasará como parámetro a la vista y al formulario.
    :param nombre_modelo: Nombre del modelo a crear. Si no se proporciona, se obtiene del formulario.

    :return: Renderizado de la plantilla con el formulario o redirección a la vista de éxito.
    """

    # Obtengo el nombre de los modelos
    nombre_modelo_secundario = nombre(modelo_secundario) if modelo_secundario else None
    nombre_modelo = nombre_modelo or nombre_verbose(formulario_modelo._meta.model)
 
    if request.method == "POST":
        # Si el formulario tiene parámetros adicionales, los paso al formulario
        form = formulario(formulario_modelo, modelo_secundario, request=request)

        # Si hay un modelo secundario, lo agrego a los datos del formulario
        if modelo_secundario:
            request.POST._mutable = True
            request.POST[nombre_modelo_secundario] = modelo_secundario.id
        
        try: 
            es_valido = form.is_valid()
        except Exception as e:
            # Si hay un error al validar el formulario, muestro mensaje de error
            messages.error(request, ERROR_CREAR.format(nombre_modelo, str(e)))
            return render(request, template, contexto(form, modelo_secundario=modelo_secundario, contexto_adicional=contexto_adicional))

        if es_valido:
            # Si el formulario es válido, guardo el modelo
            try:
                modelo = form.save()
                # Si hay función para luego de guardar, la llamo
                if func_post_save:
                    func_post_save(modelo, form)
            except Exception as e:
                # Si hay un error al guardar, muestro mensaje de error
                messages.error(request, ERROR_CREAR.format(nombre_modelo, str(e)))
                return render(request, template, contexto(form, modelo_secundario=modelo_secundario, contexto_adicional=contexto_adicional))
            # Muestro mensaje de éxito y redirijo a la vista de éxito
            messages.success(request, EXITO_CREAR.format(nombre_modelo))
            if params_vista_exito:
                return redirect(reverse(vista_exito, kwargs=params_vista_exito))
            return redirect(vista_exito)
        else:
            # Si el formulario no es válido, muestro mensaje de error
            messages.error(request, ERROR_FORMULARIO_INVALIDO.format(form.errors.as_text()))
    else:
        # Si el método no es POST, creo el formulario
        form = formulario(formulario_modelo, modelo_secundario)

    # Renderizo la plantilla con el contexto
    return render(request, template, contexto(form, modelo_secundario=modelo_secundario, contexto_adicional=contexto_adicional))


def gestionar_modelo(
    request,
    id_modelo,
    formulario_modelo,
    template,
    func_pre_save=None,
    modelo_secundario=None,
    contexto_adicional=None,
    vista_exito=None,
):
    """ 
    Vista general para gestionar un modelo.
    Si el método de la solicitud es POST, se actualiza el modelo y se muestra un mensaje de éxito.
    Si el método de la solicitud es GET, se renderiza el formulario con los datos del modelo.
    En caso de error, se muestra un mensaje correspondiente.

    :param request: Objeto HttpRequest.
    :param id_modelo: ID del modelo a gestionar.
    :param formulario_modelo: Clase del formulario a utilizar.
    :param template: Plantilla a renderizar.
    :param func_pre_save: Función a ejecutar antes de guardar el modelo.
    :param modelo_secundario: Modelo secundario relacionado. Este se pasará como parámetro a la vista y al formulario.
    :param contexto_adicional: Diccionario de contexto adicional a pasar a la plantilla.

    :return: Renderizado de la plantilla con el formulario.
    """

    modelo = get_object_or_404(formulario_modelo._meta.model, id=id_modelo)
    nombre_modelo = nombre_verbose(modelo)
    nombre_modelo_secundario = nombre(modelo_secundario) if modelo_secundario else None

    if request.method == "POST":
        with transaction.atomic():
            form = formulario(formulario_modelo, modelo_secundario, request, modelo)

            # Si hay función para luego de guardar, la llamo
            if func_pre_save: 
                try:
                    form = func_pre_save(modelo) or form
                except Exception as e:
                    # Si hay un error en la función, muestro mensaje de error
                    messages.error(request, ERROR_ACTUALIZAR.format(nombre_modelo, str(e)))
                    return render(request, template, contexto(form, modelo, modelo_secundario, contexto_adicional))

            # Si hay un modelo secundario, lo agrego a los datos del formulario
            if modelo_secundario:
                request.POST._mutable = True
                request.POST[nombre_modelo_secundario] = modelo_secundario.id

            try: 
                es_valido = form.is_valid()
            except Exception as e:
                # Si hay un error al validar el formulario, muestro mensaje de error
                messages.error(request, ERROR_CREAR.format(nombre_modelo, str(e)))
                return render(request, template, contexto(form, modelo_secundario=modelo_secundario, contexto_adicional=contexto_adicional))

            if es_valido:
                # Si el formulario es válido, guardo el modelo
                try:
                    modelo = form.save()
                except Exception as e:
                    # Si hay un error al guardar, muestro mensaje de error
                    messages.error(request, ERROR_ACTUALIZAR.format(nombre_modelo, str(e)))
                    return render(request, template, contexto(form, modelo, modelo_secundario, contexto_adicional))

                # Muestro mensaje de éxito y redirijo a la vista de éxito
                messages.success(request, EXITO_ACTUALIZAR.format(nombre_modelo))
            else:
                # Si el formulario no es válido, muestro mensaje de error
                messages.error(request, ERROR_ACTUALIZAR.format(nombre_modelo, form.errors.as_text()))
    else:
        # Si el método no es POST, creo el formulario
        form = formulario(formulario_modelo, modelo_secundario, modelo=modelo)

    if vista_exito and request.method == "POST" and form.is_valid():
        return redirect(vista_exito)

    # Renderizo la plantilla con el contexto
    return render(request, template, contexto(form, modelo, modelo_secundario, contexto_adicional))

#####################################################################
#                            AUXILIARES                             #
#####################################################################

def contexto(form, modelo=None, modelo_secundario=None, contexto_adicional=None):
    """ Función auxiliar para crear el contexto de la plantilla. """
    
    contexto = {"formulario": form}
    if modelo: contexto[nombre(modelo)] = modelo
    if modelo_secundario: contexto[nombre(modelo_secundario)] = modelo_secundario
    if contexto_adicional: contexto.update(contexto_adicional)
    return contexto

def formulario(formulario_modelo, modelo_secundario, request=None, modelo=None):
    """ Función auxiliar para crear un formulario de un modelo. """

    kwargs = {}
    
    # Si hay datos del request, los agregamos como data
    if request:
        kwargs["data"] = request.POST

    # Si hay una instancia del modelo principal, la agregamos
    if modelo:
        kwargs["instance"] = modelo

    # Si hay un modelo secundario, lo agregamos a los kwargs
    if modelo_secundario:
        kwargs[nombre(modelo_secundario)] = modelo_secundario

    return formulario_modelo(**kwargs)

def nombre(modelo):
    return modelo._meta.model_name

def nombre_verbose(modelo):
    return modelo._meta.verbose_name.lower()