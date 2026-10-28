from consorcios.models import Consorcio
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
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

    def administra(self, consorcio_id):
        """
        Verifica si el administrador administra un consorcio específico.

        :param consorcio_id: ID del consorcio a verificar.
        :return: True si el administrador administra el consorcio, False en caso contrario.
        """
        return self.consorcios.filter(id=consorcio_id).exists()

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

    def __str__(self):
        return self.usuario.get_full_name()


class InvitacionPropietario(models.Model):
    """Invitación de un propietario para vincular una UF a una cuenta."""
    unidad_funcional = models.OneToOneField(
        'consorcios.UnidadFuncional', on_delete=models.CASCADE,
        related_name='invitacion_propietario',
    )
    email = models.EmailField()
    token_hash = models.CharField(max_length=64, unique=True)
    creada = models.DateTimeField(auto_now_add=True)
    expira = models.DateTimeField()
    enviada = models.DateTimeField(null=True, blank=True)
    aceptada = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Invitación de propietario'
        verbose_name_plural = 'Invitaciones de propietarios'

    @property
    def vigente(self):
        return self.aceptada is None and self.expira > timezone.now()

    def __str__(self):
        return f"Invitación a {self.email} para {self.unidad_funcional}"
