from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, Div
from django_flatpickr.widgets import DatePickerInput
from .models import Consorcio

class FormularioConsorcio(forms.ModelForm):
    """
    Formulario para crear o editar un consorcio.
    """
    
    class Meta:
        model = Consorcio
        fields = [
            "nombre",
            "cuit",
            "fecha_creacion",
            "calle",
            "altura",
            "codigo_postal"
        ]
        widgets = {
            "fecha_creacion": DatePickerInput()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'

        self.helper.layout = Layout(
            Row(
                Column('nombre'),
                Column('cuit'),
                Column('fecha_creacion'),
                Column('calle'),
                Column('altura'),
                Column('codigo_postal'),
                css_class = 'row'
            ),
            Div(Submit('submit', 'Aceptar', css_class='boton-primario'), css_class='flex wrap center')
        )