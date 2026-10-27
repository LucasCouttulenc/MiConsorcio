from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, Div, HTML
from django_flatpickr.widgets import DatePickerInput
from django_select2.forms import Select2Widget
from usuarios.models import Propietario,Administrador
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

from django.contrib.auth import get_user_model
from usuarios.models import Propietario
from crispy_forms.layout import HTML # Asegurate de que HTML esté importado

class FormularioUnidadFuncional(forms.ModelForm):
    """
    Formulario para crear o editar una unidad funcional.
    Permite elegir un propietario existente O crear uno nuevo.
    """
    propietario = forms.ModelChoiceField(
        queryset=Propietario.objects.all(), 
        required=False, 
        widget=Select2Widget(attrs={'data-placeholder': 'Buscar propietario existente...'}),
        label="Propietario existente"
    )
    
    # Campos para el nuevo propietario
    nuevo_nombre = forms.CharField(max_length=100, required=False, label="Nombre (Nuevo)")
    nuevo_apellido = forms.CharField(max_length=100, required=False, label="Apellido (Nuevo)")
    nuevo_email = forms.EmailField(required=False, label="Email (Nuevo)")

    class Meta:
        model = UnidadFuncional
        fields = ["propietario", "consorcio", "piso", "departamento"]

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

        self.helper.layout = Layout(
            Row(
                Column('propietario'),
                Column('consorcio'),
                css_class='row'
            ),
            HTML("<div style='text-align: center; margin: 1rem 0; color: #64748b; font-weight: 600;'>— O si es un propietario nuevo, completá estos campos —</div>"),
            Row(
                Column('nuevo_nombre'),
                Column('nuevo_apellido'),
                Column('nuevo_email'),
                css_class='row'
            ),
            Row(
                Column('piso'),
                Column('departamento'),
                css_class='row'
            ),
            Div(Submit('submit', 'Aceptar', css_class='boton-primario'), css_class='flex wrap center')
        )

    def clean(self):
        cleaned_data = super().clean()
        propietario = cleaned_data.get('propietario')
        nuevo_nombre = cleaned_data.get('nuevo_nombre')
        nuevo_email = cleaned_data.get('nuevo_email')

        # Validación 1: Al menos uno de los dos métodos debe estar completo
        if not propietario and not (nuevo_nombre and nuevo_email):
            raise forms.ValidationError("Tenés que seleccionar un propietario existente o completar al menos el Nombre y Email para crear uno nuevo.")
        
        # Validación 2: Si va a crear uno nuevo, nos aseguramos que el email no exista ya en la BD
        if not propietario and nuevo_email:
            User = get_user_model()
            if User.objects.filter(username=nuevo_email).exists():
                self.add_error('nuevo_email', f"El email {nuevo_email} ya está registrado en el sistema.")
        
        return cleaned_data

    def save(self, commit=True):
        """
        Sobrescribimos el save para interceptar la creación.
        Si no hay propietario pero hay datos de uno nuevo, lo creamos ANTES de guardar la UF.
        """
        instance = super().save(commit=False)
        
        if not instance.propietario_id and self.cleaned_data.get('nuevo_email'):
            User = get_user_model()
            email = self.cleaned_data['nuevo_email']
            
            # Creamos el usuario
            user = User.objects.create_user(
                username=email,
                email=email,
                first_name=self.cleaned_data.get('nuevo_nombre'),
                last_name=self.cleaned_data.get('nuevo_apellido', ''),
                password='Consorcio1234' # Contraseña por defecto
            )
            
            # Creamos el Propietario y se lo asignamos a la instancia de la UF
            propietario = Propietario.objects.create(usuario=user)
            instance.propietario = propietario

        # Recién ahora que la UF tiene un propietario_id válido, la guardamos en la DB
        if commit:
            instance.save()
            
        return instance