"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from usuarios import views as views_usuarios
from gastos import views as views_gastos
from consorcios import views as views_consorcios
from consultas import views as views_consultas
from documentos import views as views_documentos

urlpatterns = [
    path('admin/', admin.site.urls),

    # Usuarios
    path('', views_usuarios.login, name='login'),
    path('cerrar-sesion/', auth_views.LogoutView.as_view(next_page='login'), name='cerrar_sesion'),
    path('usuarios/login/', views_usuarios.login, name='login'),
    path('usuarios/bienvenida/', views_usuarios.bienvenida, name='bienvenida'),

    # Consorcios
    path('consorcios/listar/', views_consorcios.ListarConsorcios.as_view(), name='listar_consorcios'),
    path('consorcios/gestionar/<int:id>/', views_consorcios.gestionar_consorcio, name='gestionar_consorcio'),
    path('consorcios/crear/', views_consorcios.crear_consorcio, name='crear_consorcio'),
    path('consorcios/unidades/listar', views_consorcios.ListarUnidadesFuncionales.as_view(), name='listar_unidades_funcionales'),
    re_path(r'^consorcios/(?:(?P<consorcio_id>[0-9]+)/)?unidades/crear/$', views_consorcios.crear_unidad_funcional, name='crear_unidad_funcional'),
    path('consorcios/unidades/<int:unidad_id>/gestionar/', views_consorcios.gestionar_unidad_funcional, name='gestionar_unidad_funcional'),
    path('consorcios/<int:consorcio_id>/personal/', views_consorcios.ListarPersonal.as_view(), name='listar_personal'),
    path('consorcios/<int:consorcio_id>/personal/agregar/', views_consorcios.crear_personal, name='crear_personal'),
    path('consorcios/personal/<int:personal_id>/gestionar/', views_consorcios.gestionar_personal, name='gestionar_personal'),
    path('consorcios/<int:consorcio_id>/alicuotas/',views_consorcios.definir_alicuotas,name='definir_alicuotas'),
    path('consorcios/columnas/', views_consorcios.configurar_columnas, name='configurar_columnas'),
    path('consorcios/columnas/rubro/<int:rubro_id>/', views_consorcios.editar_columnas_rubro, name='editar_columnas_rubro'),
    
    # Liquidaciones
    path('liquidaciones/', views_gastos.listar_liquidaciones, name='listar_liquidaciones'),
    path('servicios-recurrentes/', views_gastos.servicios_recurrentes, name='servicios_recurrentes'),
    path('liquidaciones/generar/', views_gastos.generar_liquidacion, name='generar_liquidacion'),
    path('liquidaciones/borradores/<int:liquidacion_id>/', views_gastos.generar_liquidacion, name='editar_liquidacion'),
    path('liquidaciones/autoguardar/', views_gastos.autosave_liquidacion, name='autosave_liquidacion'),
    path('liquidaciones/finalizar/', views_gastos.finalizar_liquidacion, name='finalizar_liquidacion'),
    path('liquidaciones/<int:liquidacion_id>/', views_gastos.detalle_liquidacion, name='detalle_liquidacion'),
    path('liquidaciones/<int:liquidacion_id>/documento/', views_gastos.descargar_documento, name='descargar_documento'),
    path('liquidaciones/gastos/<int:gasto_id>/comprobante/', views_gastos.subir_comprobante, name='subir_comprobante'),
    path('liquidaciones/gastos/<int:gasto_id>/comprobante/quitar/', views_gastos.quitar_comprobante, name='quitar_comprobante'),
    path('liquidaciones/gastos/<int:gasto_id>/comprobante/visibilidad/', views_gastos.alternar_visibilidad_comprobante, name='visibilidad_comprobante'),
    path('inicio/', views_gastos.inicio_propietario, name='inicio_propietario'),
    path('consultas/', views_consultas.mis_consultas, name='mis_consultas'),
    path('documentos/', views_documentos.mis_documentos, name='mis_documentos'),
    path('administracion/documentos/', views_documentos.documentos_consorcio, name='documentos_consorcio'),
    path('administracion/documentos/<int:documento_id>/borrar/', views_documentos.borrar_documento, name='borrar_documento'),
    path('consultas/nueva/', views_consultas.nueva_consulta, name='nueva_consulta'),
    path('consultas/<int:consulta_id>/', views_consultas.ver_consulta, name='ver_consulta'),
    path('administracion/consultas/', views_consultas.bandeja_consultas, name='bandeja_consultas'),
    path('administracion/consultas/<int:consulta_id>/', views_consultas.gestionar_consulta, name='gestionar_consulta'),
    path('mis-expensas/', views_gastos.mis_expensas, name='mis_expensas'),
    path('historial-pagos/', views_gastos.historial_pagos, name='historial_pagos'),
    path('pagos/<int:pago_id>/recibo/', views_gastos.descargar_recibo_pago, name='recibo_pago'),
    path('notificaciones/liquidacion/<int:notificacion_id>/', views_gastos.abrir_notificacion_liquidacion, name='abrir_notificacion_liquidacion'),
    path('mis-expensas/liquidacion/<int:liquidacion_id>/documento/', views_gastos.descargar_documento_propietario, name='documento_liquidacion_propietario'),
    path('liquidaciones/detalle/<int:detalle_id>/pagar/', views_gastos.registrar_pago, name='registrar_pago'),
    path('pagos/pendientes/', views_gastos.listar_pagos_pendientes, name='pagos_pendientes'),
    path('pagos/<int:pago_id>/procesar/', views_gastos.procesar_pago, name='procesar_pago'),
    path('liquidaciones/detalle-uf/<int:detalle_id>/resumen/',views_gastos.descargar_resumen_uf,name='descargar_resumen_uf'),
    path('liquidaciones/<int:liquidacion_id>/eliminar/', views_gastos.eliminar_borrador, name='eliminar_borrador'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
