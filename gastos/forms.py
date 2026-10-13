# gastos/forms.py
import os
import re
from datetime import date

from django import forms
from consorcios.models import Consorcio, GrupoProrrateo
from .models import Pago, ServicioRecurrente

PERIODO_RE = re.compile(r'(20\d\d|2100)-(0[1-9]|1[0-2])')

EXTENSIONES_COMPROBANTE = {'.pdf', '.jpg', '.jpeg', '.png'}
TIPOS_COMPROBANTE = {'application/pdf', 'image/jpeg', 'image/png'}
TAMANIO_MAXIMO_COMPROBANTE = 5 * 1024 * 1024


def validar_comprobante(archivo):
    """
    Solo acepta PDF, JPG o PNG de hasta 5 MB. Se valida la extensión además del
    content type (que lo manda el navegador y se puede falsificar), porque el
    archivo se sirve desde /media/ según su extensión.
    """
    extension = os.path.splitext(archivo.name)[1].lower()
    if extension not in EXTENSIONES_COMPROBANTE or getattr(archivo, 'content_type', None) not in TIPOS_COMPROBANTE:
        raise forms.ValidationError('El comprobante debe ser PDF, JPG o PNG.')
    if archivo.size > TAMANIO_MAXIMO_COMPROBANTE:
        raise forms.ValidationError('El comprobante no puede superar los 5 MB.')
    return archivo

class FormularioGenerarLiquidacion(forms.Form):
    consorcio = forms.ModelChoiceField(queryset=Consorcio.objects.all(), label="Consorcio")
    periodo = forms.CharField(max_length=7, help_text="Formato AAAA-MM (ej: 2026-03)", label="Período")
    fecha_vencimiento_1 = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label="Fecha 1° Vencimiento")

class FormularioPago(forms.ModelForm):
    class Meta:
        model = Pago
        fields = ['fecha_pago', 'monto_pagado', 'comprobante']
        widgets = {
            'fecha_pago': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_monto_pagado(self):
        monto = self.cleaned_data.get('monto_pagado')
        if monto is not None and monto <= 0:
            raise forms.ValidationError('El monto tiene que ser positivo.')
        return monto

    def clean_fecha_pago(self):
        fecha = self.cleaned_data.get('fecha_pago')
        if fecha and fecha > date.today():
            raise forms.ValidationError('La fecha de pago no puede ser futura.')
        return fecha

    def clean_comprobante(self):
        return validar_comprobante(self.cleaned_data['comprobante'])

class FormularioServicioRecurrente(forms.ModelForm):
    class Meta:
        model = ServicioRecurrente
        fields = ['concepto', 'proveedor', 'columna', 'tipo', 'monto_sugerido',
                  'frecuencia_meses', 'periodo_inicio', 'periodo_fin']
        widgets = {
            'periodo_inicio': forms.TextInput(attrs={'type': 'month'}),
            'periodo_fin': forms.TextInput(attrs={'type': 'month'}),
        }

    def __init__(self, *args, consorcio, **kwargs):
        super().__init__(*args, **kwargs)
        self.consorcio = consorcio
        self.fields['columna'].queryset = GrupoProrrateo.objects.filter(
            consorcio=consorcio).select_related('rubro').order_by('rubro__nombre', 'codigo')

    def _validar_periodo(self, campo):
        valor = (self.cleaned_data.get(campo) or '').strip()
        if not valor:
            return ''
        if not PERIODO_RE.fullmatch(valor):
            raise forms.ValidationError('Usá el formato AAAA-MM.')
        return valor

    def clean_periodo_inicio(self):
        valor = self._validar_periodo('periodo_inicio')
        if not valor:
            raise forms.ValidationError('Indicá desde qué período se aplica.')
        return valor

    def clean_periodo_fin(self):
        return self._validar_periodo('periodo_fin')

    def clean_monto_sugerido(self):
        monto = self.cleaned_data.get('monto_sugerido')
        if monto is not None and monto <= 0:
            raise forms.ValidationError('El monto tiene que ser positivo.')
        return monto

    def clean(self):
        datos = super().clean()
        inicio, fin = datos.get('periodo_inicio'), datos.get('periodo_fin')
        if inicio and fin and fin < inicio:
            self.add_error('periodo_fin', 'El último período no puede ser anterior al primero.')
        return datos

    def save(self, commit=True):
        self.instance.consorcio = self.consorcio
        return super().save(commit)
