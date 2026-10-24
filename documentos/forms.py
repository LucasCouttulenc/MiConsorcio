import os

from django import forms

from .models import DocumentoConsorcio

EXTENSIONES_DOCUMENTO = {'.pdf', '.jpg', '.jpeg', '.png'}
TAMANIO_MAXIMO_DOCUMENTO = 10 * 1024 * 1024


class FormularioDocumento(forms.ModelForm):
    class Meta:
        model = DocumentoConsorcio
        fields = ['tipo', 'titulo', 'archivo', 'vencimiento']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'sin-select2'}),
            # Campo nativo dd/mm/aaaa: se tipea de izquierda a derecha y solo acepta fechas válidas.
            'vencimiento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo'].choices = [('', 'Elegí el tipo')] + list(self.fields['tipo'].choices)[1:]

    def clean_archivo(self):
        archivo = self.cleaned_data['archivo']
        if os.path.splitext(archivo.name)[1].lower() not in EXTENSIONES_DOCUMENTO:
            raise forms.ValidationError('El documento debe ser PDF, JPG o PNG.')
        if archivo.size > TAMANIO_MAXIMO_DOCUMENTO:
            raise forms.ValidationError('El documento no puede superar los 10 MB.')
        return archivo
