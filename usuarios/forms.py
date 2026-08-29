from django import forms
from django.contrib.auth.forms import AuthenticationForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Div, Submit

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