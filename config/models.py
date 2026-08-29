from django_tables2.export.views import ExportMixin
from django.shortcuts import redirect

class ExportMixinCustom(ExportMixin):
    def get(self, request, *args, **kwargs):
        # Si el usuario no tiene permisos para exportar, se redirige a la misma página.
        if '_export' in request.GET: #and not request.user.has_perm(self.permiso_para_exportar):
            return redirect(request.path)
        
        return super().get(request, *args, **kwargs)