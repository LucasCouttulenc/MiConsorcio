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
from django.contrib.auth import views as auth_views
from usuarios import views as views_usuarios
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
]
