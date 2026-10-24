from datetime import date, timedelta

from django.db import models

from consorcios.models import Consorcio

DIAS_AVISO_VENCIMIENTO = 30


class TipoDocumento(models.TextChoices):
    REGLAMENTO = 'reglamento', 'Reglamento de copropiedad'
    POLIZA = 'poliza', 'Póliza de seguro'
    CERTIFICADO = 'certificado', 'Certificado'
    OTRO = 'otro', 'Otro'


class DocumentoConsorcio(models.Model):
    """Documento del edificio que la administración comparte con los propietarios."""
    consorcio = models.ForeignKey(Consorcio, on_delete=models.CASCADE, related_name='documentos')
    tipo = models.CharField(max_length=15, choices=TipoDocumento.choices, verbose_name="Tipo")
    titulo = models.CharField(max_length=150, verbose_name="Título", help_text="Ej: Certificado de ascensores")
    archivo = models.FileField(upload_to='documentos/%Y/%m/', verbose_name="Archivo")
    vencimiento = models.DateField(null=True, blank=True, verbose_name="Vence el",
                                   help_text="Para pólizas y certificados. Dejalo vacío si no vence.")
    subido = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Documento del consorcio"
        verbose_name_plural = "Documentos del consorcio"
        ordering = ['tipo', 'titulo']

    def __str__(self):
        return f"{self.titulo} ({self.consorcio.nombre})"

    @property
    def estado_vencimiento(self):
        """'vigente', 'por_vencer' (dentro de los próximos 30 días), 'vencido' o None si no vence."""
        if not self.vencimiento:
            return None
        hoy = date.today()
        if self.vencimiento < hoy:
            return 'vencido'
        if self.vencimiento <= hoy + timedelta(days=DIAS_AVISO_VENCIMIENTO):
            return 'por_vencer'
        return 'vigente'
