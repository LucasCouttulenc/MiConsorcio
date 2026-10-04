# gastos/forms.py
from django import forms
from consorcios.models import Consorcio
from .models import Pago

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