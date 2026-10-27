from django.db import models

from consorcios.models import Consorcio


class ContactoAdministracion(models.Model):
    """Datos de contacto de la administración que ve el propietario. Todos son opcionales."""
    consorcio = models.OneToOneField(Consorcio, on_delete=models.CASCADE, related_name='contacto_administracion')
    nombre = models.CharField(max_length=150, blank=True, default='', verbose_name="Nombre de la administración")
    direccion = models.CharField(max_length=150, blank=True, default='', verbose_name="Dirección")
    localidad = models.CharField(max_length=100, blank=True, default='', verbose_name="Localidad")
    telefono = models.CharField(max_length=30, blank=True, default='', verbose_name="Teléfono")
    horario = models.CharField(max_length=100, blank=True, default='', verbose_name="Horario de atención")
    email = models.EmailField(blank=True, default='', verbose_name="Email")
    sitio_web = models.URLField(blank=True, default='', verbose_name="Sitio web")

    class Meta:
        verbose_name = "Contacto de la administración"
        verbose_name_plural = "Contactos de la administración"

    def __str__(self):
        return f"Administración de {self.consorcio.nombre}"

    @property
    def esta_vacio(self):
        return not any((self.nombre, self.direccion, self.localidad, self.telefono,
                        self.horario, self.email, self.sitio_web))


class TelefonoUtil(models.Model):
    """Servicios y urgencias del consorcio (encargado, ascensores, gas, emergencias...)."""
    consorcio = models.ForeignKey(Consorcio, on_delete=models.CASCADE, related_name='telefonos_utiles')
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    telefono = models.CharField(max_length=30, verbose_name="Teléfono")
    detalle = models.CharField(max_length=150, blank=True, default='', verbose_name="Detalle")

    class Meta:
        verbose_name = "Teléfono útil"
        verbose_name_plural = "Teléfonos útiles"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre}: {self.telefono}"
