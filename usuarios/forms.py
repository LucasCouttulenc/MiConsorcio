from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Div, Submit

User = get_user_model()

class FormularioLogin(AuthenticationForm):
    """
    Formulario de inicio de sesión configurado con Crispy Forms.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        error_messages = {
            'invalid_login': (
                "El correo electrónico o la contraseña son incorrectos. "
                "Por favor, verificá los datos ingresados."
            ),
            'inactive': "Esta cuenta se encuentra inactiva.",
        }
        self.error_messages = error_messages

        # Ajustamos etiquetas y placeholders de los campos heredados
        self.fields['username'].label = "Correo electrónico"
        self.fields['username'].widget.attrs.update({
            'placeholder': 'Ingrese su correo electrónico',
            'autocomplete': 'off',
        })

        self.fields['password'].label = "Contraseña"
        self.fields['password'].widget.attrs.update({
            'placeholder': 'Ingrese su contraseña',
            'autocomplete': 'new-password',
        })

        # Configuración del Helper y Layout
        self.helper = FormHelper()
        self.helper.form_method = 'POST'
        self.helper.form_class = 'formulario-inicio-sesion flex column'

        self.helper.layout = Layout(
            Row(
                Column('username', css_class='formulario-inicio-sesion__campo flex column'),
                css_class='row'
            ),
            Row(
                Column('password', css_class='formulario-inicio-sesion__campo flex column'),
                css_class='row'
            ),
            Div(
                Submit('ingresar', 'Ingresar', css_class='boton-primario'),
                css_class='flex center column contenedor-boton'
            )
        )


class FormularioRegistroPropietario(forms.Form):
    email = forms.EmailField(label='Correo electrónico', disabled=True)
    nombre = forms.CharField(max_length=150, label='Nombre')
    apellido = forms.CharField(max_length=150, label='Apellido')
    password = forms.CharField(
        label='Contraseña', strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )
    confirmar_password = forms.CharField(
        label='Confirmar contraseña', strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    def __init__(self, *args, email, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].initial = email
        self.email_invitacion = email

    def clean(self):
        datos = super().clean()
        password = datos.get('password')
        confirmar = datos.get('confirmar_password')
        if password and confirmar and password != confirmar:
            self.add_error('confirmar_password', 'Las contraseñas no coinciden.')
        elif password:
            usuario = User(
                username=self.email_invitacion, email=self.email_invitacion,
                first_name=datos.get('nombre', ''), last_name=datos.get('apellido', ''),
            )
            try:
                validate_password(password, user=usuario)
            except ValidationError as error:
                self.add_error('password', error)
        return datos


class FormularioConfirmarCuenta(forms.Form):
    """Pide la contraseña de una cuenta existente antes de sumarle la UF de la invitación."""
    email = forms.EmailField(label='Correo electrónico', disabled=True)
    password = forms.CharField(
        label='Contraseña de tu cuenta', strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].initial = usuario.email or usuario.username
        self.usuario = usuario

    def clean_password(self):
        password = self.cleaned_data['password']
        if not self.usuario.check_password(password):
            raise ValidationError('La contraseña es incorrecta.')
        return password
