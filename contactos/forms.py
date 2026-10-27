from django import forms

from .models import ContactoAdministracion, TelefonoUtil


class FormularioContactoAdministracion(forms.ModelForm):
    class Meta:
        model = ContactoAdministracion
        fields = ['nombre', 'telefono', 'email', 'direccion', 'localidad', 'horario', 'sitio_web']


class FormularioTelefonoUtil(forms.ModelForm):
    class Meta:
        model = TelefonoUtil
        fields = ['nombre', 'telefono', 'detalle']
