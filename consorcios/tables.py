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
        exclude = ('id',)
        # sequence = ('direccion',...
    
    # Acciones

    gestionar = TemplateColumn(
        template_code='<a href="{% url "gestionar_consorcio" record.id %}" class="tabla__boton-accion-registro">Gestionar</a>',
        verbose_name="Gestionar",
        orderable=False,
        exclude_from_export=True
    )
    """Botón que redirige a la vista de gestión de la beca."""


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