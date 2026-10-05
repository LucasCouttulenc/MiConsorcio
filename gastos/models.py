from django.db import models
from consorcios.models import Consorcio, UnidadFuncional, GrupoProrrateo

class TipoGasto(models.TextChoices):
    ORDINARIO = 'ordinario'
    EXTRAORDINARIO = 'extraordinario'


class Gasto(models.Model):
    consorcio = models.ForeignKey(Consorcio, on_delete=models.CASCADE, related_name='gastos')
    concepto = models.CharField(max_length=200, verbose_name="Concepto del Gasto")
    monto = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto")
    tipo = models.CharField(
        max_length=20, 
        choices=TipoGasto.choices, 
        default=TipoGasto.ORDINARIO, 
        verbose_name="Tipo de Gasto"
    )
    subtipo = models.CharField(max_length=100, blank=True, default='', verbose_name="Subtipo / Rubro")
    grupo = models.ForeignKey(GrupoProrrateo, on_delete=models.PROTECT, related_name='gastos', null=True, blank=True, verbose_name="Columna / Grupo de Prorrateo")
    periodo = models.CharField(max_length=7, help_text="Formato AAAA-MM (ej: 2026-03)", verbose_name="Período Imputado")
    fecha_comprobante = models.DateField(verbose_name="Fecha del Comprobante")
    liquidacion = models.ForeignKey('Liquidacion', on_delete=models.CASCADE, related_name='gastos_cargados', null=True, blank=True)
    posicion = models.PositiveIntegerField(default=0)
    comprobante = models.FileField(upload_to='comprobantes/%Y/%m/', null=True, blank=True, verbose_name="Comprobante / Factura")

    class Meta:
        verbose_name = "Gasto"
        verbose_name_plural = "Gastos"

    def __str__(self):
        return f"{self.concepto} - ${self.monto} [{self.get_tipo_display()} - {self.grupo.codigo if self.grupo else '-'}]"


class Liquidacion(models.Model):
    consorcio = models.ForeignKey(Consorcio, on_delete=models.CASCADE, related_name='liquidaciones')
    periodo = models.CharField(max_length=7, help_text="Formato AAAA-MM", verbose_name="Período Liquidado")
    fecha_emision = models.DateField(auto_now_add=True, verbose_name="Fecha de Emisión")
    fecha_cierre = models.DateField(null=True, blank=True, verbose_name="Fecha de Cierre")
    fecha_vencimiento_1 = models.DateField(null=True, blank=True, verbose_name="Primer Vencimiento")
    total_ordinario = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_extraordinario = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    cerrada = models.BooleanField(default=False, verbose_name="¿Cerrada?")
    datos_borrador = models.JSONField(default=dict, blank=True)
    documento = models.BinaryField(null=True, blank=True)
    actualizada = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        unique_together = ('consorcio', 'periodo')
        verbose_name = "Liquidación"
        verbose_name_plural = "Liquidaciones"

    def __str__(self):
        return f"Liquidación {self.consorcio.nombre} - Período {self.periodo}"

    @property
    def total(self):
        return self.total_ordinario + self.total_extraordinario

    @property
    def cantidad_gastos_borrador(self):
        return sum(1 for gasto in self.datos_borrador.get('gastos', []) if gasto.get('concepto') or gasto.get('monto'))


class DetalleLiquidacionUF(models.Model):
    liquidacion = models.ForeignKey(Liquidacion, on_delete=models.CASCADE, related_name='detalles_uf')
    unidad_funcional = models.ForeignKey(UnidadFuncional, on_delete=models.CASCADE)
    alicuota = models.DecimalField(
        max_digits=6, decimal_places=4, default=0,
        verbose_name="Alícuota aplicada (%)",
    )
    monto_ordinario = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    monto_extraordinario = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    monto_total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    class Meta:
        verbose_name = "Detalle Expensa por UF"
        verbose_name_plural = "Detalles Expensas por UF"

    def __str__(self):
        return f"UF {self.unidad_funcional} - Período {self.liquidacion.periodo}: ${self.monto_total}"