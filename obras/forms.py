from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Div, Layout, Row, Submit
from django import forms
from django_flatpickr.widgets import DatePickerInput

from .models import AsignacionProveedor, Obra, Proveedor


def proveedores_visibles(usuario):
    """Proveedores que el usuario puede ver y asignar: los que cargó él (el superusuario ve todos)."""
    if usuario.is_superuser:
        return Proveedor.objects.all()
    return Proveedor.objects.filter(creado_por=usuario)


class FormularioObra(forms.ModelForm):
    class Meta:
        model = Obra
        fields = ['concepto', 'estado', 'fecha_inicio', 'fecha_fin_estimada', 'descripcion']
        widgets = {
            'fecha_inicio': DatePickerInput(),
            'fecha_fin_estimada': DatePickerInput(),
            'descripcion': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        consorcio = kwargs.pop('consorcio', None)  # debe estar en la primera línea
        super().__init__(*args, **kwargs)
        if consorcio:
            self.instance.consorcio = consorcio

        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.layout = Layout(
            Row(Column('concepto'), Column('estado'), css_class='row'),
            Row(Column('fecha_inicio'), Column('fecha_fin_estimada'), css_class='row'),
            Row(Column('descripcion'), css_class='row'),
            Div(Submit('submit', 'Guardar', css_class='boton-primario'), css_class='flex wrap center')
        )

    def clean(self):
        datos = super().clean()
        inicio, fin = datos.get('fecha_inicio'), datos.get('fecha_fin_estimada')
        if inicio and fin and inicio > fin:
            self.add_error('fecha_fin_estimada', 'La fecha de fin no puede ser anterior a la de inicio.')
        return datos


class FormularioProveedor(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['nombre', 'razon_social', 'telefono', 'email']

    def __init__(self, *args, **kwargs):
        usuario = kwargs.pop('user', None)  # debe estar en la primera línea
        super().__init__(*args, **kwargs)
        if usuario and not self.instance.pk:
            self.instance.creado_por = usuario

        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.layout = Layout(
            Row(Column('nombre'), Column('razon_social'), css_class='row'),
            Row(Column('telefono'), Column('email'), css_class='row'),
            Div(Submit('submit', 'Guardar', css_class='boton-primario'), css_class='flex wrap center')
        )


class FormularioAsignacion(forms.ModelForm):
    class Meta:
        model = AsignacionProveedor
        fields = ['proveedor', 'tarea']

    def __init__(self, *args, obra, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.obra = obra
        self.fields['proveedor'].queryset = proveedores_visibles(usuario).exclude(asignaciones__obra=obra)
        self.fields['proveedor'].empty_label = 'Elegí un proveedor'
