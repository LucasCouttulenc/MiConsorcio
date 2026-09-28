from django.db import models

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

    def __str__(self):
        return f"{self.nombre} - {self.calle} {self.altura}, CP {self.codigo_postal}"

    def save(self, *args, **kwargs):
        # Validar que el CUIT tenga 11 dígitos
        if len(self.cuit) != 11 or not self.cuit.isdigit():
            raise ValueError("El CUIT debe tener 11 dígitos numéricos.")
        super().save(*args, **kwargs)

class GrupoProrrateo(models.Model):
    """
    Columna/Rubro de prorrateo dinámico (ej: "A - General", "B - Ascensores", "Fachada")
    """
    consorcio = models.ForeignKey(Consorcio, on_delete=models.CASCADE, related_name='grupos_prorrateo')
    nombre = models.CharField(max_length=100, verbose_name="Nombre del Grupo/Columna")
    codigo = models.CharField(max_length=10, help_text="Ej: A, B, C, PISCINA", verbose_name="Código / Identificador")

    class Meta:
        verbose_name = "Grupo de Prorrateo"
        verbose_name_plural = "Grupos de Prorrateo"
        unique_together = ('consorcio', 'codigo')

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

    def __str__(self):
        return f"{self.piso}° {self.departamento} (Propietario: {self.propietario})"

    def save(self, *args, **kwargs):
        if UnidadFuncional.objects.filter(consorcio=self.consorcio, piso=self.piso, departamento=self.departamento).exclude(id=self.id).exists():
            raise ValueError("Ya existe una unidad funcional con el mismo piso y departamento en este consorcio.")
        super().save(*args, **kwargs)


class CoeficienteUF(models.Model):
    """
    Porcentaje asignado a una Unidad Funcional para una Columna/Grupo específico
    """
    unidad_funcional = models.ForeignKey(UnidadFuncional, on_delete=models.CASCADE, related_name='coeficientes')
    grupo = models.ForeignKey(GrupoProrrateo, on_delete=models.CASCADE, related_name='coeficientes_uf')
    porcentaje = models.DecimalField(max_digits=6, decimal_places=4, default=0.0000, verbose_name="Porcentaje / Coeficiente")

    class Meta:
        verbose_name = "Coeficiente UF"
        verbose_name_plural = "Coeficientes UF"
        unique_together = ('unidad_funcional', 'grupo')

    def __str__(self):
        return f"{self.unidad_funcional} - {self.grupo.codigo}: {self.porcentaje}%"