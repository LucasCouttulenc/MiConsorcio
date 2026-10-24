from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, Div
from django_flatpickr.widgets import DatePickerInput
from django_select2.forms import Select2Widget
from usuarios.models import Administrador
from .models import *

class FormularioConsorcio(forms.ModelForm):
    """
    Formulario para crear o editar un consorcio.
    """
    
    class Meta:
        model = Consorcio
        fields = [
            "nombre",
            "cuit",
            "clave_suterh",
            "fecha_creacion",
            "calle",
            "altura",
            "codigo_postal",
            "localidad",
            "horario_atencion",
            "tasa_interes_mensual",
        ]
        widgets = {
            "fecha_creacion": DatePickerInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'

        # Reorganizamos las columnas para que queden 3 por fila
        self.helper.layout = Layout(
            Row(
                Column('nombre'),
                Column('cuit'),
                Column('clave_suterh'),
                css_class = 'row'
            ),
            Row(
                Column('fecha_creacion'),
                Column('calle'),
                Column('altura'),
                css_class = 'row'
            ),
            Row(
                Column('codigo_postal'),
                Column('localidad'),
                Column('horario_atencion'),
                css_class = 'row'
            ),
            Row(
                Column('tasa_interes_mensual'),
                Column(),
                Column(),
                css_class = 'row'
            ),
            Div(Submit('submit', 'Aceptar', css_class='boton-primario'), css_class='flex wrap center')
        )
class FormularioPersonal(forms.ModelForm):
    """
    Formulario para crear o editar personal de un consorcio.
    """

    class Meta:
        model = Personal
        fields = [
            "consorcio",
            "nombre",
            "apellido",
            "dni",
            "cargo",
            "tipo_contratacion",
            "empresa_tercerizada",
            "telefono",
            "fecha_ingreso",
        ]
        widgets = {
            "fecha_ingreso": DatePickerInput(),
        }

    def __init__(self, *args, **kwargs):
        consorcio = kwargs.pop('consorcio', None) # debe estar en la primera línea
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        if consorcio:
            self.fields['consorcio'].queryset = Consorcio.objects.filter(id=consorcio.id)
            self.fields['consorcio'].initial = consorcio

        self.fields['consorcio'].disabled = True

        # El DNI no debe poder modificarse una vez creado el registro
        if self.instance and self.instance.pk:
            self.fields['dni'].disabled = True

        self.helper.layout = Layout(
            Row(
                Column('consorcio'),
                Column('nombre'),
                Column('apellido'),
                Column('dni'),
                css_class='row'
            ),
            Row(
                Column('cargo'),
                Column('tipo_contratacion'),
                Column('empresa_tercerizada'),
                css_class='row'
            ),
            Row(
                Column('telefono'),
                Column('fecha_ingreso'),
                css_class='row'
            ),
            Div(Submit('submit', 'Aceptar', css_class='boton-primario'), css_class='flex wrap center')
        )

class FormularioUnidadFuncional(forms.ModelForm):
    class Meta:
        model = UnidadFuncional
        fields = ["propietario", "consorcio", "piso", "departamento"]
        widgets = {
            "propietario": Select2Widget(attrs={'data-placeholder': 'Seleccione un propietario'}),
        }

    def __init__(self, *args, **kwargs):
        # Extraemos los argumentos que pueden venir
        usuario = kwargs.pop('user', None)
        consorcio = kwargs.pop('consorcio', None)
        
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'POST'

        if consorcio:
            # SI VENIMOS DE UN CONSORCIO: lo bloqueamos
            self.fields['consorcio'].queryset = Consorcio.objects.filter(id=consorcio.id)
            self.fields['consorcio'].initial = consorcio
            self.fields['consorcio'].disabled = True
        elif usuario:
            # SI VENIMOS DEL PANEL GENERAL: filtramos según el usuario
            if usuario.is_superuser:
                self.fields['consorcio'].queryset = Consorcio.objects.all()
            else:
                administrador = Administrador.objects.filter(usuario=usuario).first()
                if administrador:
                    self.fields['consorcio'].queryset = administrador.consorcios.all()
                else:
                    self.fields['consorcio'].queryset = Consorcio.objects.none()

        self.helper.layout = Layout(
            Row(
                Column('propietario'),
                Column('consorcio'),
                css_class='row'
            ),
            Row(
                Column('piso'),
                Column('departamento'),
                css_class='row'
            ),
            Div(Submit('submit', 'Aceptar', css_class='boton-primario'), css_class='flex wrap center')
        )