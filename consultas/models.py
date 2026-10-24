from django.conf import settings
from django.db import models

from consorcios.models import UnidadFuncional


class EstadoConsulta(models.TextChoices):
    ABIERTA = 'abierta', 'Abierta'
    EN_CURSO = 'en_curso', 'En curso'
    CERRADA = 'cerrada', 'Cerrada'


class Consulta(models.Model):
    """Consulta o reclamo que un propietario le hace a la administración sobre una de sus UF."""
    unidad_funcional = models.ForeignKey(UnidadFuncional, on_delete=models.CASCADE, related_name='consultas')
    asunto = models.CharField(max_length=150, verbose_name="Asunto")
    estado = models.CharField(max_length=10, choices=EstadoConsulta.choices, default=EstadoConsulta.ABIERTA)
    creada = models.DateTimeField(auto_now_add=True)
    actualizada = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Consulta"
        verbose_name_plural = "Consultas"
        ordering = ['-actualizada']

    def __str__(self):
        return f"#{self.pk} {self.asunto} ({self.get_estado_display()})"

    @property
    def cerrada(self):
        return self.estado == EstadoConsulta.CERRADA


class MensajeConsulta(models.Model):
    """Cada mensaje del hilo: el primero es la descripción del propietario."""
    consulta = models.ForeignKey(Consulta, on_delete=models.CASCADE, related_name='mensajes')
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mensajes_consulta')
    de_administracion = models.BooleanField(default=False)
    texto = models.TextField(max_length=3000, verbose_name="Mensaje")
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mensaje de consulta"
        verbose_name_plural = "Mensajes de consultas"
        ordering = ['creado', 'pk']

    def __str__(self):
        return f"Mensaje de {self.autor} en {self.consulta}"
