from django.contrib import admin

from .models import ServicioRecurrente


@admin.register(ServicioRecurrente)
class ServicioRecurrenteAdmin(admin.ModelAdmin):
    list_display = ('concepto', 'consorcio', 'columna', 'frecuencia_meses', 'periodo_inicio', 'periodo_fin', 'activo')
    list_filter = ('consorcio', 'activo', 'frecuencia_meses')
