from django import forms

from .models import Consulta


class FormularioConsulta(forms.ModelForm):
    """Nueva consulta del propietario: la UF sale de las suyas y la descripción es el primer mensaje."""
    descripcion = forms.CharField(
        label="Descripción", max_length=3000,
        widget=forms.Textarea(attrs={'rows': 5, 'placeholder': 'Contanos qué pasa, desde cuándo y dónde.'}),
    )

    class Meta:
        model = Consulta
        fields = ['unidad_funcional', 'asunto']
        labels = {'unidad_funcional': 'Unidad funcional'}
        widgets = {'asunto': forms.TextInput(attrs={'placeholder': 'Ej: Pérdida de agua en el techo del baño'})}

    def __init__(self, *args, unidades=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['unidad_funcional'].queryset = unidades
        self.fields['unidad_funcional'].label_from_instance = lambda uf: (
            f"{uf.consorcio.nombre} · Piso {uf.piso}" + (f" · Depto. {uf.departamento}" if uf.departamento else "")
        )
        self.fields['unidad_funcional'].empty_label = None


class FormularioMensaje(forms.Form):
    texto = forms.CharField(
        label="Respuesta", max_length=3000,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Escribí tu mensaje'}),
    )
