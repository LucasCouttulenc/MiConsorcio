from django.db import models

#####################################################################
#                          CONSORCIO                                #
#####################################################################

class Consorcio(models.Model):
    """
    Modelo que representa a un consorcio, esto es un conjunto de unidades funcionales que comparten gastos y servicios.
    """

    class Meta:
        verbose_name = "Consorcio"
        verbose_name_plural = "Consorcios"

    nombre = models.CharField(max_length=50, unique=True, verbose_name="Nombre")
    """Nombre identificatorio del consorcio (ej. Moldes 123)"""    

    cuit = models.CharField(max_length=11,verbose_name="CUIT", unique=True)
    """CUIT del consorcio (ej. 30123456759)"""

    clave_suterh = models.CharField(max_length=50, unique=True, verbose_name="Clave SUTERH", default=None, null=True, blank=True)
    """Clave SUTERH del consorcio, utilizada para la gestión de empleados y aportes sindicales."""

    fecha_creacion = models.DateField(verbose_name="Fecha de creación")
    """Fecha en la que se creó el consorcio en el sistema."""

    calle = models.CharField(max_length=150)

    altura = models.PositiveIntegerField()

    codigo_postal = models.IntegerField(verbose_name="Código Postal")

    # TODO: datos sobre banco/liquidaciones, etc.?

    def __str__(self):
        return f"{self.nombre} - {self.calle} {self.altura}, CP {self.codigo_postal}"

#####################################################################
#                          UNIDAD FUNCIONAL                         #
#####################################################################

class UnidadFuncional(models.Model):
    """
    Modelo que representa a una unidad funcional dentro de un consorcio, como un departamento o una oficina con un propietario asociado.
    """

    class Meta:
        verbose_name = "Unidad Funcional"
        verbose_name_plural = "Unidades Funcionales"

    propietario = models.ForeignKey('usuarios.Propietario', on_delete=models.CASCADE)
    consorcio = models.ForeignKey(Consorcio, on_delete=models.CASCADE)
    piso = models.PositiveIntegerField(verbose_name="Piso")
    departamento = models.CharField(max_length=10, verbose_name="Departamento", blank=True, null=True)

    # TODO agregar campos específicos para la unidad funcional.

    def __str__(self):
        return f"{self.piso} - {self.departamento} (Propietario: {self.propietario})"

    def save(self, *args, **kwargs):
        # Si existe una unidad funcional con el mismo piso y departamento en el mismo consorcio, no se permite guardar.
        if UnidadFuncional.objects.filter(consorcio=self.consorcio, piso=self.piso, departamento=self.departamento).exclude(id=self.id).exists():
            raise ValueError("Ya existe una unidad funcional con el mismo piso y departamento en este consorcio.")

        super().save(*args, **kwargs)