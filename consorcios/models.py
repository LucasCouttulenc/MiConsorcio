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
        
    direccion = models.CharField(max_length=255, unique=True, verbose_name="Dirección")

    # TODO agregar campos específicos para el administrador.


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

    