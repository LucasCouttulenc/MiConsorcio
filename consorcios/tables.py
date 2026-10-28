import django_filters
from django_tables2 import tables
from django_tables2 import TemplateColumn
from django.forms import Select, TextInput
from django.db.models import Q

from usuarios.models import Administrador
from .models import *
from config.comun import GRUPO_ADMINISTRADORES



    
class TablaPersonal(tables.Table):

    class Meta:
        model = Personal
        template_name = "tabla.html"
        exclude = ('id', 'consorcio')
        sequence = ('nombre', 'apellido', 'dni', 'cargo', 'tipo_contratacion', 'empresa_tercerizada', 'telefono', 'fecha_ingreso', '...')

    gestionar = TemplateColumn(
        template_code='<a href="{% url "gestionar_personal" record.id %}" class="tabla__boton-accion-registro">Gestionar</a>',
        verbose_name="Gestionar",
        orderable=False,
        exclude_from_export=True
    )
    """Botón que redirige a la vista de gestión del personal."""

    def render_tipo_contratacion(self, record):
        return record.get_tipo_contratacion_display()


class FiltroPersonal(django_filters.FilterSet):
    texto = django_filters.CharFilter(
        method="filtrar_por_texto",
        label="Buscar",
        widget=TextInput(attrs={"placeholder": "Buscar por nombre, apellido o cargo"}),
    )
    tipo_contratacion = django_filters.ChoiceFilter(
        choices=Personal.TIPO_CONTRATACION,
        label="Tipo de contratación",
        empty_label="Todos",
    )

    class Meta:
        model = Personal
        fields = ["texto", "tipo_contratacion"]

    def filtrar_por_texto(self, queryset, name, value) -> models.QuerySet:
        """
        Filtra el queryset de personal por nombre, apellido o cargo.

        :param queryset: QuerySet de personal.
        :param name: Nombre del campo a filtrar (no se usa en este caso).
        :param value: Valor por el cual se filtra.
        :return: QuerySet filtrado.
        :rtype: QuerySet[Personal]
        """

        return queryset.filter(
            Q(nombre__icontains=value) |
            Q(apellido__icontains=value) |
            Q(cargo__icontains=value) |
            Q(dni__icontains=value)
        )


class TablaUnidadesFuncionales(tables.Table):
    
    class Meta:
        model = UnidadFuncional
        template_name = "tabla.html"
        exclude = ('id', )
        # sequence = ('direccion',...

    consorcio = tables.columns.Column(accessor='consorcio.nombre', verbose_name='Consorcio')
    
    
    alicuota = tables.columns.Column(verbose_name="Alícuota (%)")

    def render_alicuota(self, value):
        if value is not None:
            return f"{value:.0f}%" # Convierte a entero (ej: 20.0000 -> 20)
        return "-"

    def render_propietario(self, value, record):
        if value:
            return value
        invitacion = getattr(record, 'invitacion_propietario', None)
        if invitacion:
            return f'Invitación pendiente · {invitacion.email}'
        return 'Sin propietario asignado'

    # Acciones
    gestionar = TemplateColumn(
        template_code='<a href="{% url "gestionar_unidad_funcional" record.id %}" class="tabla__boton-accion-registro">Modificar</a>',
        verbose_name="Gestionar",
        orderable=False,
        exclude_from_export=True
    )
    """Botón que redirige a la vista de gestión de la unidad funcional."""
    
    
class FiltroUnidadesFuncionales(django_filters.FilterSet):
    texto = django_filters.CharFilter(
        method="filtrar_por_texto",
        label="Buscar",
        widget=TextInput(attrs={"placeholder": "Buscar por piso, depto o propietario"}),
    )

    class Meta:
        model = UnidadFuncional
        fields = ["texto"]

    def filtrar_por_texto(self, queryset, name, value) -> models.QuerySet:
        """
        Filtra el queryset de unidades funcionales por texto.
        """
        return queryset.filter(
            Q(piso__icontains=value) |
            Q(departamento__icontains=value) |
            Q(propietario__usuario__first_name__icontains=value) |
            Q(propietario__usuario__last_name__icontains=value) |
            Q(invitacion_propietario__email__icontains=value)
        )
