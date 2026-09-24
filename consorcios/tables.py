import django_filters
from django_tables2 import tables
from django_tables2 import TemplateColumn
from django.forms import TextInput
from django.db.models import Q
from .models import *

class TablaConsorcios(tables.Table):

    class Meta:
        model = Consorcio
        template_name = "tabla.html"
        exclude = ('id', 'clave_suterh')
        # sequence = ('direccion',...
    
    # Acciones

    gestionar = TemplateColumn(
        template_code='<a href="{% url "gestionar_consorcio" record.id %}" class="tabla__boton-accion-registro">Gestionar</a>',
        verbose_name="Gestionar",
        orderable=False,
        exclude_from_export=True
    )
    """Botón que redirige a la vista de gestión de la beca."""

    unidades = TemplateColumn(
        template_code='<a href="{% url "listar_unidades_funcionales" record.id %}" class="tabla__boton-accion-registro">Unidades</a>',
        verbose_name="Unidades",
        orderable=False,
        exclude_from_export=True
    )
    """Botón que redirige a la vista de gestión de las unidades funcionales del consorcio."""


class FiltroConsorcios(django_filters.FilterSet):
    direccion = django_filters.CharFilter(
        method="filtrar_por_texto",
        label="Buscar",
        widget=TextInput(attrs={"placeholder": "Buscar"}),
    )

    class Meta:
        model = Consorcio
        fields = ["direccion"]

    def filtrar_por_texto(self, queryset, name, value)-> models.QuerySet:
        """
        Filtra el queryset de becas por el nombre de la beca.

        :param queryset: QuerySet de becas.
        :param name: Nombre del campo a filtrar (no se usa en este caso).
        :param value: Valor por el cual se filtra (nombre de la beca).
        :return: QuerySet filtrado por el nombre de la beca.
        :rtype: QuerySet[Beca]
        """

        return queryset.filter(Q(direccion__icontains=value))
    
class TablaUnidadesFuncionales(tables.Table):
    
    class Meta:
        model = UnidadFuncional
        template_name = "tabla.html"
        exclude = ('id', 'consorcio')
        # sequence = ('direccion',...
    
    # Acciones

    # gestionar = TemplateColumn(
    #     template_code='<a href="{% url "gestionar_unidad_funcional" record.id %}" class="tabla__boton-accion-registro">Gestionar</a>',
    #     verbose_name="Gestionar",
    #     orderable=False,
    #     exclude_from_export=True
    # )
    # """Botón que redirige a la vista de gestión de la unidad funcional."""

class FiltroUnidadesFuncionales(django_filters.FilterSet):
    direccion = django_filters.CharFilter(
        method="filtrar_por_texto",
        label="Buscar",
        widget=TextInput(attrs={"placeholder": "Buscar"}),
    )

    class Meta:
        model = UnidadFuncional
        fields = ["direccion"]

    def filtrar_por_texto(self, queryset, name, value)-> models.QuerySet:
        """
        Filtra el queryset de unidades funcionales por el nombre de la unidad funcional.

        :param queryset: QuerySet de unidades funcionales.
        :param name: Nombre del campo a filtrar (no se usa en este caso).
        :param value: Valor por el cual se filtra (nombre de la unidad funcional).
        :return: QuerySet filtrado por el nombre de la unidad funcional.
        :rtype: QuerySet[UnidadFuncional]
        """

        return queryset.filter(Q(direccion__icontains=value))