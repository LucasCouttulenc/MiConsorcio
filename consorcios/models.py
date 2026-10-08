from django.db import models
from django.utils import timezone


#####################################################################
#                          CONSORCIO                               #
#####################################################################

class Consorcio(models.Model):
    class Meta:
        verbose_name = "Consorcio"
        verbose_name_plural = "Consorcios"

    nombre = models.CharField(max_length=50, unique=True, verbose_name="Nombre")
    cuit = models.CharField(max_length=11, verbose_name="CUIT", unique=True)
    clave_suterh = models.CharField(max_length=50, unique=True, verbose_name="Clave SUTERH", default=None, null=True, blank=True)
    fecha_creacion = models.DateField(verbose_name="Fecha de creación")
    calle = models.CharField(max_length=150)
    altura = models.PositiveIntegerField()
    codigo_postal = models.IntegerField(verbose_name="Código Postal")
    localidad = models.CharField(max_length=100, blank=True, default='', verbose_name="Localidad")
    horario_atencion = models.CharField(max_length=100, blank=True, default='', verbose_name="Horario de atención")

    def __str__(self):
        return f"{self.nombre} - {self.calle} {self.altura}, CP {self.codigo_postal}"

    def save(self, *args, **kwargs):
        # Validar que el CUIT tenga 11 dígitos
        if len(self.cuit) != 11 or not self.cuit.isdigit():
            raise ValueError("El CUIT debe tener 11 dígitos numéricos.")

        # Validar que la fecha de creación no sea futura
        if self.fecha_creacion > timezone.now().date():
            raise ValueError("La fecha de creación no puede ser futura.")

        super().save(*args, **kwargs)


#####################################################################
#                            RUBRO                                  #
#####################################################################

class Rubro(models.Model):
    """
    Categoría contable del consorcio (ej: "REMUNERACIONES AL PERSONAL",
    "SERVICIOS PÚBLICOS", "ARREGLO DE CAÑERÍAS").
    Cada rubro agrupa columnas de prorrateo.
    """
    consorcio = models.ForeignKey(
        Consorcio, on_delete=models.CASCADE, related_name='rubros'
    )
    nombre = models.CharField(max_length=100, verbose_name="Nombre del Rubro")

    class Meta:
        verbose_name = "Rubro"
        verbose_name_plural = "Rubros"
        unique_together = ('consorcio', 'nombre')
        ordering = ['nombre']

    def __str__(self):
        return f"{self.consorcio.nombre} - {self.nombre}"


#####################################################################
#                         TIPO DE REPARTO                           #
#####################################################################

class TipoReparto(models.TextChoices):
    GENERAL = 'general', 'General'
    PARCIAL = 'parcial', 'Parcial'
    PARTICULAR = 'particular', 'Particular'


#####################################################################
#                         GRUPO PRORRATEO                           #
#####################################################################

class GrupoProrrateo(models.Model):
    """
    Columna de prorrateo que pertenece a un Rubro (ej: "A - General",
    "B - Ascensores", "Fachada").
    """
    consorcio = models.ForeignKey(Consorcio, on_delete=models.CASCADE, related_name='grupos_prorrateo')
    rubro = models.ForeignKey(Rubro, on_delete=models.CASCADE, related_name='columnas')
    nombre = models.CharField(max_length=100, verbose_name="Nombre del Grupo/Columna")
    codigo = models.CharField(max_length=10, help_text="Ej: A, B, C, PISCINA", verbose_name="Código / Identificador")
    tipo_reparto = models.CharField(max_length=20, choices=TipoReparto.choices, default=TipoReparto.GENERAL, verbose_name="Tipo de reparto")
    unidades = models.ManyToManyField('UnidadFuncional', blank=True, related_name='columnas', verbose_name="UF afectadas / exentas", help_text="Particular: UF que pagan. Parcial: UF exentas. General: se ignora.")

    class Meta:
        verbose_name = "Grupo de Prorrateo"
        verbose_name_plural = "Grupos de Prorrateo"
        unique_together = ('consorcio', 'rubro', 'codigo')

    def __str__(self):
        return f"{self.consorcio.nombre} - Columna {self.codigo} ({self.nombre})"


#####################################################################
#                          UNIDAD FUNCIONAL                         #
#####################################################################

class UnidadFuncional(models.Model):
    class Meta:
        verbose_name = "Unidad Funcional"
        verbose_name_plural = "Unidades Funcionales"

    propietario = models.ForeignKey('usuarios.Propietario', on_delete=models.CASCADE)
    consorcio = models.ForeignKey(Consorcio, on_delete=models.CASCADE, related_name='unidades_funcionales')
    piso = models.PositiveIntegerField(verbose_name="Piso")
    departamento = models.CharField(max_length=10, verbose_name="Departamento", blank=True, null=True)
    alicuota = models.DecimalField(
        max_digits=6, decimal_places=4, default=0,
        verbose_name="Alícuota (%)",
        help_text="Porcentaje que le corresponde a esta UF sobre el total del consorcio.",
    )

    def __str__(self):
        return f"{self.piso}° {self.departamento} (Propietario: {self.propietario})"

    def save(self, *args, **kwargs):
        if UnidadFuncional.objects.filter(
            consorcio=self.consorcio, piso=self.piso, departamento=self.departamento
        ).exclude(id=self.id).exists():
            raise ValueError("Ya existe una unidad funcional con el mismo piso y departamento en este consorcio.")
        super().save(*args, **kwargs)


#####################################################################
#                             PERSONAL                              #
#####################################################################

class Personal(models.Model):
    class Meta:
        verbose_name = "Personal"
        verbose_name_plural = "Personal"

    TIPO_CONTRATACION = [
        ("directo", "Relación de dependencia"),
        ("tercerizado", "Tercerizado"),
    ]

    consorcio = models.ForeignKey(Consorcio, on_delete=models.CASCADE, related_name='personal')
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    apellido = models.CharField(max_length=100, verbose_name="Apellido")
    dni = models.CharField(max_length=20, verbose_name="DNI")
    cargo = models.CharField(max_length=100, verbose_name="Cargo", help_text="Ej: Encargado, Portero, Limpieza")
    tipo_contratacion = models.CharField(max_length=20, choices=TIPO_CONTRATACION, default="directo", verbose_name="Tipo de contratación")
    empresa_tercerizada = models.CharField(max_length=150, blank=True, default='', verbose_name="Empresa tercerizada")
    telefono = models.CharField(max_length=30, blank=True, default='', verbose_name="Teléfono")
    fecha_ingreso = models.DateField(null=True, blank=True, verbose_name="Fecha de ingreso")

    def __str__(self):
        return f"{self.apellido}, {self.nombre} ({self.cargo})"


#####################################################################
#                          COEFICIENTE UF                           #
#####################################################################

class CoeficienteUF(models.Model):
    """
    Legacy: se mantiene por compatibilidad de migraciones. No se usa en el
    cálculo nuevo (que usa UnidadFuncional.alicuota).
    """
    unidad_funcional = models.ForeignKey(UnidadFuncional, on_delete=models.CASCADE, related_name='coeficientes')
    grupo = models.ForeignKey(GrupoProrrateo, on_delete=models.CASCADE, related_name='coeficientes_uf')
    porcentaje = models.DecimalField(max_digits=7, decimal_places=4, default=0, verbose_name="Porcentaje / Coeficiente")

    class Meta:
        verbose_name = "Coeficiente UF"
        verbose_name_plural = "Coeficientes UF"
        unique_together = ('unidad_funcional', 'grupo')

    def __str__(self):
        return f"{self.unidad_funcional} - {self.grupo.codigo}: {self.porcentaje}%"