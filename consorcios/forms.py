from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, Div, HTML
from django_flatpickr.widgets import DatePickerInput
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
            "fondo_reserva_nombre",
            "fondo_reserva_porcentaje",
        ]
        widgets = {
            "fecha_creacion": DatePickerInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'POST'

        # Agrupamos los campos en secciones para que el formulario se lea más fácil
        self.helper.layout = Layout(
            HTML('<h3 class="form-seccion-titulo">Datos generales</h3>'),
            Row(
                Column('nombre'),
                Column('cuit'),
                Column('clave_suterh'),
                Column('fecha_creacion'),
                css_class = 'row'
            ),
            HTML('<h3 class="form-seccion-titulo">Dirección y atención</h3>'),
            Row(
                Column('calle'),
                Column('altura'),
                Column('codigo_postal'),
                Column('localidad'),
                css_class = 'row'
            ),
            Row(
                Column('horario_atencion'),
                css_class = 'row'
            ),
            HTML('<h3 class="form-seccion-titulo">Cobranza</h3>'),
            Row(
                Column('tasa_interes_mensual'),
                Column('fondo_reserva_nombre'),
                Column('fondo_reserva_porcentaje'),
                css_class = 'row'
            ),
            Div(Submit('submit', 'Guardar cambios', css_class='boton-primario'), css_class='flex wrap center')
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
    """
    Formulario para crear o editar una unidad funcional.
    La UF se crea sin propietario y se vincula cuando acepta la invitación enviada por correo.
    """
    email_propietario = forms.EmailField(label="Correo del propietario")

    class Meta:
        model = UnidadFuncional
        fields = ["consorcio", "piso", "departamento"]

    def __init__(self, *args, **kwargs):
        consorcio = kwargs.pop('consorcio', None)
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        
        if consorcio:
            self.fields['consorcio'].queryset = Consorcio.objects.filter(id=consorcio.id)
            self.fields['consorcio'].initial = consorcio
            
        # Bloqueamos el campo consorcio siempre
        self.fields['consorcio'].disabled = True

        if self.instance and self.instance.pk and self.instance.propietario_id:
            self.fields['email_propietario'].initial = self.instance.propietario.usuario.email
            self.fields['email_propietario'].disabled = True
            self.fields['email_propietario'].required = False
            self.fields['email_propietario'].help_text = 'Esta UF ya está vinculada a un propietario.'
        elif self.instance and self.instance.pk:
            invitacion = getattr(self.instance, 'invitacion_propietario', None)
            if invitacion:
                self.fields['email_propietario'].initial = invitacion.email

        self.helper.layout = Layout(
            Row(
                Column('email_propietario'),
                Column('consorcio'),
                css_class='row'
            ),
            HTML("<p class='uf-invitacion-ayuda'>Si el correo ya tiene cuenta, la unidad se suma directo; si no, le enviamos un link para que cree su cuenta.</p>"),
            Row(
                Column('piso'),
                Column('departamento'),
                css_class='row'
            ),
            Div(Submit(
                'submit',
                'Guardar cambios' if self.instance and self.instance.pk and self.instance.propietario_id
                else ('Guardar y reenviar invitación' if self.instance and self.instance.pk else 'Crear UF y enviar invitación'),
                css_class='boton-primario',
            ), css_class='flex wrap center')
        )
