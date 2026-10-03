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
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from usuarios import views as views_usuarios
from gastos import views as views_gastos
from consorcios import views as views_consorcios

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
    path('consorcios/<int:consorcio_id>/unidades/', views_consorcios.ListarUnidadesFuncionales.as_view(), name='listar_unidades_funcionales'),
    path('consorcios/<int:consorcio_id>/unidades/crear/', views_consorcios.crear_unidad_funcional, name='crear_unidad_funcional'),
    path('consorcios/unidades/<int:unidad_id>/gestionar/', views_consorcios.gestionar_unidad_funcional, name='gestionar_unidad_funcional'),
    path('consorcios/<int:consorcio_id>/personal/', views_consorcios.ListarPersonal.as_view(), name='listar_personal'),
    path('consorcios/<int:consorcio_id>/personal/agregar/', views_consorcios.crear_personal, name='crear_personal'),
    path('consorcios/personal/<int:personal_id>/gestionar/', views_consorcios.gestionar_personal, name='gestionar_personal'),
      path('consorcios/<int:consorcio_id>/alicuotas/',views_consorcios.definir_alicuotas,name='definir_alicuotas'),
    # Liquidaciones
    path('liquidaciones/', views_gastos.listar_liquidaciones, name='listar_liquidaciones'),
    path('liquidaciones/generar/', views_gastos.generar_liquidacion, name='generar_liquidacion'),
    path('liquidaciones/borradores/<int:liquidacion_id>/', views_gastos.generar_liquidacion, name='editar_liquidacion'),
    path('liquidaciones/autoguardar/', views_gastos.autosave_liquidacion, name='autosave_liquidacion'),
    path('liquidaciones/finalizar/', views_gastos.finalizar_liquidacion, name='finalizar_liquidacion'),
    path('liquidaciones/<int:liquidacion_id>/', views_gastos.detalle_liquidacion, name='detalle_liquidacion'),
    path('liquidaciones/<int:liquidacion_id>/documento/', views_gastos.descargar_documento, name='descargar_documento'),
    path('liquidaciones/gastos/<int:gasto_id>/comprobante/', views_gastos.subir_comprobante, name='subir_comprobante'),
    path('liquidaciones/gastos/<int:gasto_id>/comprobante/quitar/', views_gastos.quitar_comprobante, name='quitar_comprobante'),
   
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
