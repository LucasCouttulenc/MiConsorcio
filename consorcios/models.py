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

    # TODO agregar campos específicos para la unidad funcional.

    