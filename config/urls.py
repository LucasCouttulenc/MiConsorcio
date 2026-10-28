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
from gastos import morosidad as views_morosidad
from gastos import convenios as views_convenios
from consorcios import views as views_consorcios
from consultas import views as views_consultas
from documentos import views as views_documentos
from contactos import views as views_contactos
from obras import views as views_obras

urlpatterns = [
    path('admin/', admin.site.urls),

    # Usuarios
    path('', views_usuarios.login, name='login'),
    path('cerrar-sesion/', auth_views.LogoutView.as_view(next_page='login'), name='cerrar_sesion'),
    path('usuarios/login/', views_usuarios.login, name='login'),
    path('usuarios/bienvenida/', views_usuarios.bienvenida, name='bienvenida'),
    path('invitacion/propietario/<str:token>/', views_usuarios.aceptar_invitacion_propietario, name='aceptar_invitacion_propietario'),
    path('cambiar-consorcio/', views_usuarios.cambiar_consorcio_activo, name='cambiar_consorcio_activo'),
    
    # Consorcios
    path('consorcios/datos/', views_consorcios.gestionar_consorcio, name='gestionar_consorcio'),
    path('consorcios/crear/', views_consorcios.crear_consorcio, name='crear_consorcio'),
    
    # Unidades 
    path('consorcios/unidades/', views_consorcios.ListarUnidadesFuncionales.as_view(), name='listar_unidades_funcionales'),
    path('consorcios/unidades/crear/', views_consorcios.crear_unidad_funcional, name='crear_unidad_funcional'),
    path('consorcios/unidades/<int:unidad_id>/gestionar/', views_consorcios.gestionar_unidad_funcional, name='gestionar_unidad_funcional'),
    
    # Personal 
    path('consorcios/personal/', views_consorcios.ListarPersonal.as_view(), name='listar_personal'),
    path('consorcios/personal/agregar/', views_consorcios.crear_personal, name='crear_personal'),
    path('consorcios/personal/<int:personal_id>/gestionar/', views_consorcios.gestionar_personal, name='gestionar_personal'),
    
    # Obras y proveedores
    path('obras/', views_obras.ListarObras.as_view(), name='listar_obras'),
    path('obras/registrar/', views_obras.crear_obra, name='crear_obra'),
    path('obras/<int:obra_id>/', views_obras.gestionar_obra, name='gestionar_obra'),
    path('obras/<int:obra_id>/asignar/', views_obras.asignar_proveedor, name='asignar_proveedor'),
    path('obras/asignaciones/<int:asignacion_id>/quitar/', views_obras.quitar_asignacion, name='quitar_asignacion'),
    path('proveedores/', views_obras.ListarProveedores.as_view(), name='listar_proveedores'),
    path('proveedores/registrar/', views_obras.crear_proveedor, name='crear_proveedor'),
    path('proveedores/<int:proveedor_id>/', views_obras.gestionar_proveedor, name='gestionar_proveedor'),

    # Alícuotas y Rubros
    path('consorcios/alicuotas/', views_consorcios.definir_alicuotas, name='definir_alicuotas'),
    path('consorcios/columnas/', views_consorcios.configurar_columnas, name='configurar_columnas'),
    path('consorcios/columnas/rubro/<int:rubro_id>/', views_consorcios.editar_columnas_rubro, name='editar_columnas_rubro'),
    
    # Liquidaciones y gastos (TODO: separar las urls para que sea mas diferenciable)
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
    path('contactos/', views_contactos.mis_contactos, name='mis_contactos'),
    path('administracion/contactos/', views_contactos.contactos_consorcio, name='contactos_consorcio'),
    path('administracion/contactos/<int:telefono_id>/borrar/', views_contactos.borrar_telefono, name='borrar_telefono'),
    path('consultas/nueva/', views_consultas.nueva_consulta, name='nueva_consulta'),
    path('consultas/<int:consulta_id>/', views_consultas.ver_consulta, name='ver_consulta'),
    path('administracion/consultas/', views_consultas.bandeja_consultas, name='bandeja_consultas'),
    path('administracion/consultas/<int:consulta_id>/', views_consultas.gestionar_consulta, name='gestionar_consulta'),
    path('mis-expensas/', views_gastos.mis_expensas, name='mis_expensas'),
    path('historial-pagos/', views_gastos.historial_pagos, name='historial_pagos'),
    path('mi-convenio/', views_convenios.mi_convenio, name='mi_convenio'),
    path('pagos/<int:pago_id>/recibo/', views_gastos.descargar_recibo_pago, name='recibo_pago'),
    path('notificaciones/liquidacion/<int:notificacion_id>/', views_gastos.abrir_notificacion_liquidacion, name='abrir_notificacion_liquidacion'),
    path('mis-expensas/liquidacion/<int:liquidacion_id>/documento/', views_gastos.descargar_documento_propietario, name='documento_liquidacion_propietario'),
    path('liquidaciones/detalle/<int:detalle_id>/pagar/', views_gastos.registrar_pago, name='registrar_pago'),
    path('pagos/pendientes/', views_gastos.listar_pagos_pendientes, name='pagos_pendientes'),
    path('administracion/morosidad/', views_morosidad.morosidad, name='morosidad'),
    path('administracion/morosidad/uf/<int:unidad_id>/', views_morosidad.morosidad_unidad, name='morosidad_unidad'),
    path('administracion/morosidad/uf/<int:unidad_id>/convenio/', views_convenios.armar_convenio, name='armar_convenio'),
    path('pagos/<int:pago_id>/procesar/', views_gastos.procesar_pago, name='procesar_pago'),
    path('liquidaciones/detalle-uf/<int:detalle_id>/resumen/',views_gastos.descargar_resumen_uf,name='descargar_resumen_uf'),
    path('liquidaciones/<int:liquidacion_id>/eliminar/', views_gastos.eliminar_borrador, name='eliminar_borrador'),
    path('administracion/caja/', views_gastos.caja, name='caja'),
    
    
    
    # Libro Diario
    path('administracion/libro-diario/', views_gastos.libro_diario, name='libro_diario'),
    path('administracion/libro-diario/<int:gasto_id>/pagar/', views_gastos.pagar_gasto_libro, name='pagar_gasto_libro'),
    path('administracion/libro-diario/<int:gasto_id>/borrar/', views_gastos.borrar_gasto_libro, name='borrar_gasto_libro'),
    path('libro-diario/cerrar/<int:gasto_id>/', views_gastos.cerrar_gasto_libro, name='cerrar_gasto_libro'),


    #servicios recurrentes
    path('servicios-recurrentes/pagar/<int:servicio_id>/', views_gastos.pagar_servicio_recurrente, name='pagar_servicio_recurrente'),
    path('servicios-recurrentes/cerrar-caja/<int:gasto_id>/', views_gastos.cerrar_caja_servicio, name='cerrar_caja_servicio'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
