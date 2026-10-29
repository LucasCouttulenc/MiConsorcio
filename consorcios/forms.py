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
    La UF se crea sin propietario y se vincula cuando acepta la invitación enviada por correo
    (o directo, si el correo ya tiene cuenta). Cambiar el correo pasa la UF a ese otro propietario.
    """
    email_propietario = forms.EmailField(label="Correo del propietario")
    reenviar_invitacion = forms.BooleanField(
        label="Reenviar la invitación (el link anterior deja de funcionar)", required=False,
    )

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

        # Correo con el que está la UF hoy: el de su propietario o el de la invitación pendiente.
        self.email_actual = ''
        con_propietario = bool(self.instance and self.instance.pk and self.instance.propietario_id)
        if con_propietario:
            usuario = self.instance.propietario.usuario
            self.email_actual = usuario.email or usuario.username
            self.fields['email_propietario'].help_text = 'Si cambiás el correo, la UF pasa a ese otro propietario.'
        elif self.instance and self.instance.pk:
            invitacion = getattr(self.instance, 'invitacion_propietario', None)
            if invitacion:
                self.email_actual = invitacion.email
        self.fields['email_propietario'].initial = self.email_actual
        pendiente = bool(self.instance and self.instance.pk and not con_propietario)
        if not pendiente:
            del self.fields['reenviar_invitacion']

        self.helper.layout = Layout(
            Row(
                Column('email_propietario'),
                Column('consorcio'),
                css_class='row'
            ),
            Row(
                Column('piso'),
                Column('departamento'),
                css_class='row'
            ),
            'reenviar_invitacion' if pendiente else HTML(''),
            Div(Submit(
                'submit',
                'Guardar cambios' if self.instance and self.instance.pk else 'Crear UF',
                css_class='boton-primario',
            ), css_class='flex wrap center')
        )

    def email_cambio(self):
        """True si el admin cargó un correo distinto al que tenía la UF."""
        nuevo = self.cleaned_data.get('email_propietario', '').strip().lower()
        return nuevo != self.email_actual.strip().lower()
