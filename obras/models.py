from django.conf import settings
from django.db import models

from consorcios.models import Consorcio


class Proveedor(models.Model):
    """
    Proveedor de la administración. No pertenece a un consorcio: un mismo
    proveedor puede trabajar en obras de distintos consorcios del administrador.
    """
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='proveedores')
    nombre = models.CharField(max_length=150, verbose_name="Nombre")
    razon_social = models.CharField(max_length=150, blank=True, default='', verbose_name="Razón social")
    telefono = models.CharField(max_length=30, blank=True, default='', verbose_name="Teléfono")
    email = models.EmailField(blank=True, default='', verbose_name="Mail")

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class EstadoObra(models.TextChoices):
    PLANIFICADA = 'planificada', 'Planificada'
    EN_CURSO = 'en_curso', 'En curso'
    FINALIZADA = 'finalizada', 'Finalizada'
    CANCELADA = 'cancelada', 'Cancelada'


class Obra(models.Model):
    consorcio = models.ForeignKey(Consorcio, on_delete=models.CASCADE, related_name='obras')
    concepto = models.CharField(max_length=150, verbose_name="Concepto", help_text="Ej: Impermeabilización de terraza")
    descripcion = models.TextField(blank=True, default='', verbose_name="Descripción")
    estado = models.CharField(max_length=15, choices=EstadoObra.choices, default=EstadoObra.PLANIFICADA, verbose_name="Estado")
    fecha_inicio = models.DateField(verbose_name="Fecha de inicio")
    fecha_fin_estimada = models.DateField(verbose_name="Fecha de fin estimada")
    proveedores = models.ManyToManyField(Proveedor, through='AsignacionProveedor', related_name='obras', blank=True)

    class Meta:
        verbose_name = "Obra"
        verbose_name_plural = "Obras"
        ordering = ['-fecha_inicio']

    def __str__(self):
        return self.concepto


class AsignacionProveedor(models.Model):
    """Proveedor asignado a una obra y la tarea que realiza en ella."""
    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name='asignaciones')
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='asignaciones')
    tarea = models.CharField(max_length=200, verbose_name="Tarea", help_text="Ej: Provisión de membrana")

    class Meta:
        verbose_name = "Proveedor asignado"
        verbose_name_plural = "Proveedores asignados"
        unique_together = ('obra', 'proveedor')

    def __str__(self):
        return f"{self.proveedor} - {self.tarea}"
