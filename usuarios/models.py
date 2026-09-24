from consorcios.models import Consorcio
from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()

#####################################################################
#                        ADMINISTRADOR                              #
#####################################################################

class Administrador(models.Model):
    """
    Modelo que representa a un administrador de consorcios.
    """

    class Meta:
        verbose_name = "Administrador"
        verbose_name_plural = "Administradores"

    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    consorcios = models.ManyToManyField(Consorcio, related_name='administradores')

    # TODO agregar campos específicos para el administrador.

#####################################################################
#                        PROPIETARIO                               #
#####################################################################
    
class Propietario(models.Model):
    """
    Modelo que representa a un propietario de unidad en un consorcio.
    """

    class Meta:
        verbose_name = "Propietario"
        verbose_name_plural = "Propietarios"

    usuario = models.OneToOneField(User, on_delete=models.CASCADE)

    # TODO agregar campos específicos para el propietario.
