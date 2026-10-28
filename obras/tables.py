import django_filters
from django.db.models import Q
from django.forms import TextInput
from django_tables2 import Column, TemplateColumn, tables

from .models import EstadoObra, Obra, Proveedor


class TablaObras(tables.Table):
    proveedores = Column(empty_values=(), verbose_name="Proveedores", orderable=False)
    gestionar = TemplateColumn(
        template_code='<a href="{% url "gestionar_obra" record.id %}" class="tabla__boton-accion-registro">Gestionar</a>',
        verbose_name="Gestionar",
        orderable=False,
        exclude_from_export=True
    )

    class Meta:
        model = Obra
        template_name = "tabla.html"
        fields = ('concepto', 'estado', 'fecha_inicio', 'fecha_fin_estimada')

    def render_estado(self, record):
        return record.get_estado_display()

    def render_proveedores(self, record):
        return ', '.join(p.nombre for p in record.proveedores.all()) or '—'


class FiltroObras(django_filters.FilterSet):
    texto = django_filters.CharFilter(
        method="filtrar_por_texto",
        label="Buscar",
        widget=TextInput(attrs={"placeholder": "Buscar por concepto o proveedor"}),
    )
    estado = django_filters.ChoiceFilter(choices=EstadoObra.choices, label="Estado", empty_label="Todos")

    class Meta:
        model = Obra
        fields = ["texto", "estado"]

    def filtrar_por_texto(self, queryset, name, value):
        return queryset.filter(Q(concepto__icontains=value) | Q(proveedores__nombre__icontains=value)).distinct()


class TablaProveedores(tables.Table):
    obras = Column(empty_values=(), verbose_name="Obras", orderable=False)
    gestionar = TemplateColumn(
        template_code='<a href="{% url "gestionar_proveedor" record.id %}" class="tabla__boton-accion-registro">Gestionar</a>',
        verbose_name="Gestionar",
        orderable=False,
        exclude_from_export=True
    )

    class Meta:
        model = Proveedor
        template_name = "tabla.html"
        fields = ('nombre', 'razon_social', 'telefono', 'email')

    def render_obras(self, record):
        return record.asignaciones.count()


class FiltroProveedores(django_filters.FilterSet):
    texto = django_filters.CharFilter(
        method="filtrar_por_texto",
        label="Buscar",
        widget=TextInput(attrs={"placeholder": "Buscar por nombre o razón social"}),
    )

    class Meta:
        model = Proveedor
        fields = ["texto"]

    def filtrar_por_texto(self, queryset, name, value):
        return queryset.filter(Q(nombre__icontains=value) | Q(razon_social__icontains=value))
