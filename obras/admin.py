from django.contrib import admin

from .models import AsignacionProveedor, Obra, Proveedor

admin.site.register(Obra)
admin.site.register(Proveedor)
admin.site.register(AsignacionProveedor)
