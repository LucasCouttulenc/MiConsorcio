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
    grupo = models.ForeignKey(GrupoProrrateo, on_delete=models.PROTECT, related_name='gastos', null=True, blank=True, verbose_name="Columna / Grupo de Prorrateo")
    periodo = models.CharField(max_length=7, help_text="Formato AAAA-MM (ej: 2026-03)", verbose_name="Período Imputado")
    fecha_comprobante = models.DateField(verbose_name="Fecha del Comprobante")
    liquidacion = models.ForeignKey('Liquidacion', on_delete=models.CASCADE, related_name='gastos_cargados', null=True, blank=True)
    posicion = models.PositiveIntegerField(default=0)
    comprobante = models.FileField(upload_to='comprobantes/%Y/%m/', null=True, blank=True, verbose_name="Comprobante / Factura")
    servicio = models.ForeignKey('ServicioRecurrente', on_delete=models.SET_NULL, related_name='gastos', null=True, blank=True, verbose_name="Servicio recurrente de origen")

    class Meta:
        verbose_name = "Gasto"
        verbose_name_plural = "Gastos"

    def __str__(self):
        return f"{self.concepto} - ${self.monto} [{self.get_tipo_display()} - {self.grupo.codigo if self.grupo else '-'}]"
    
    @property
    def rubro(self):
        """
        El rubro viene dado por la columna (GrupoProrrateo) a la que
        pertenece el gasto. Si el gasto no tiene columna, no tiene rubro.
        """
        return self.grupo.rubro if self.grupo_id else None


def periodo_a_meses(periodo):
    """Convierte 'AAAA-MM' en un número de meses absoluto (para restar períodos)."""
    anio, mes = periodo.split('-')
    return int(anio) * 12 + int(mes) - 1


class ServicioRecurrente(models.Model):
    """
    Servicio que se repite cada N meses (ej: fumigación trimestral). No genera
    gastos solo: se propone como fila en Generar Liquidación en los períodos
    que corresponde y el administrador la confirma, edita o descarta.
    """
    FRECUENCIAS = [
        (1, 'Mensual'), (2, 'Bimestral'), (3, 'Trimestral'),
        (4, 'Cuatrimestral'), (6, 'Semestral'), (12, 'Anual'),
    ]

    consorcio = models.ForeignKey(Consorcio, on_delete=models.CASCADE, related_name='servicios_recurrentes')
    concepto = models.CharField(max_length=200, verbose_name="Concepto")
    proveedor = models.CharField(max_length=150, blank=True, default='', verbose_name="Proveedor")
    columna = models.ForeignKey(GrupoProrrateo, on_delete=models.PROTECT, related_name='servicios_recurrentes', verbose_name="Columna de prorrateo")
    tipo = models.CharField(max_length=20, choices=TipoGasto.choices, default=TipoGasto.ORDINARIO, verbose_name="Tipo de gasto")
    monto_sugerido = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Monto sugerido", help_text="Opcional: si queda vacío, el monto se completa al liquidar.")
    frecuencia_meses = models.PositiveSmallIntegerField(choices=FRECUENCIAS, default=1, verbose_name="Frecuencia")
    periodo_inicio = models.CharField(max_length=7, help_text="Formato AAAA-MM", verbose_name="Primer período")
    periodo_fin = models.CharField(max_length=7, blank=True, default='', help_text="Formato AAAA-MM. Vacío = sin fin", verbose_name="Último período")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Servicio recurrente"
        verbose_name_plural = "Servicios recurrentes"
        ordering = ['concepto']

    def __str__(self):
        return f"{self.concepto} ({self.get_frecuencia_meses_display()})"

    @property
    def rubro(self):
        return self.columna.rubro if self.columna_id else None

    def corresponde_en(self, periodo):
        """True si el servicio se tiene que proponer en el período 'AAAA-MM'."""
        if not self.activo:
            return False
        actual = periodo_a_meses(periodo)
        inicio = periodo_a_meses(self.periodo_inicio)
        if actual < inicio:
            return False
        if self.periodo_fin and actual > periodo_a_meses(self.periodo_fin):
            return False
        return (actual - inicio) % self.frecuencia_meses == 0

    def proximo_periodo(self, desde):
        """Primer período >= 'desde' en el que corresponde, o None si ya no vuelve."""
        if not self.activo:
            return None
        actual = max(periodo_a_meses(desde), periodo_a_meses(self.periodo_inicio))
        inicio = periodo_a_meses(self.periodo_inicio)
        resto = (actual - inicio) % self.frecuencia_meses
        if resto:
            actual += self.frecuencia_meses - resto
        if self.periodo_fin and actual > periodo_a_meses(self.periodo_fin):
            return None
        return f"{actual // 12:04d}-{actual % 12 + 1:02d}"


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

    @property
    def total_pagado(self):
        """Suma todos los pagos validados"""
        pagos_validos = self.pagos.filter(estado='validado')
        return sum(pago.monto_pagado for pago in pagos_validos) if pagos_validos else 0

    @property
    def deuda_total_actualizada(self):
        return self.monto_total - self.total_pagado

    @property
    def esta_pagado(self):
        return self.deuda_total_actualizada <= 0

    @property
    def tiene_pago_pendiente(self):
        return self.pagos.filter(estado='pendiente').exists()

class Pago(models.Model):
    ESTADOS = (
        ('pendiente', 'Pendiente de Validación'),
        ('validado', 'Validado'),
        ('rechazado', 'Rechazado'),
    )
    detalle_liquidacion = models.ForeignKey(DetalleLiquidacionUF, on_delete=models.CASCADE, related_name='pagos')
    fecha_pago = models.DateField(verbose_name="Fecha de pago")
    monto_pagado = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Monto pagado")
    comprobante = models.FileField(upload_to='comprobantes_pago/', verbose_name="Comprobante de transferencia")
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    fecha_registro = models.DateTimeField(auto_now_add=True)
    notas_admin = models.TextField(blank=True, default='', verbose_name="Notas del Administrador")
    
    class Meta:
        verbose_name = "Pago de Expensa"
        verbose_name_plural = "Pagos de Expensas"

    def __str__(self):
        return f"Pago de {self.detalle_liquidacion.unidad_funcional} - ${self.monto_pagado}"


class DetalleGastoUF(models.Model):
    """Importe de un gasto imputado a una unidad en una liquidación cerrada."""
    gasto = models.ForeignKey(Gasto, on_delete=models.CASCADE, related_name='distribuciones_uf')
    unidad_funcional = models.ForeignKey(UnidadFuncional, on_delete=models.CASCADE, related_name='distribuciones_gastos')
    porcentaje_aplicado = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    monto_asignado = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Distribución de gasto por UF"
        verbose_name_plural = "Distribuciones de gastos por UF"
        unique_together = ('gasto', 'unidad_funcional')

    def __str__(self):
        return f"{self.gasto.concepto} - {self.unidad_funcional}: ${self.monto_asignado}"
