from datetime import date

from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase
from django.urls import reverse

from config.comun import GRUPO_ADMINISTRADORES, GRUPO_PROPIETARIOS, PERMISOS_ADMINISTRADORES, PERMISOS_PROPIETARIOS
from usuarios.models import Administrador, Propietario

from .models import Consorcio, Personal, UnidadFuncional


def crear_consorcio(nombre='Torre Uno', cuit='30712345678'):
    return Consorcio.objects.create(
        nombre=nombre, cuit=cuit, fecha_creacion=date(2020, 1, 1),
        calle='Av. Siempre Viva', altura=742, codigo_postal=1000,
    )


def crear_usuario_administrador(username, con_registro=True):
    """Usuario del grupo Administradores; opcionalmente sin registro de Administrador."""
    grupo, _ = Group.objects.get_or_create(name=GRUPO_ADMINISTRADORES)
    grupo.permissions.set(Permission.objects.filter(codename__in=PERMISOS_ADMINISTRADORES))
    usuario = User.objects.create_user(username, password='clave')
    usuario.groups.add(grupo)
    administrador = Administrador.objects.create(usuario=usuario) if con_registro else None
    return usuario, administrador


class PermisosAdministradorTests(TestCase):
    def setUp(self):
        self.consorcio = crear_consorcio()
        self.otro = crear_consorcio('Torre Dos', '30798765432')
        self.usuario, administrador = crear_usuario_administrador('admin')
        administrador.consorcios.add(self.consorcio)
        self.client.force_login(self.usuario)

    def test_crear_uf_desde_un_consorcio_que_administra(self):
        respuesta = self.client.get(reverse('crear_unidad_funcional', args=[self.consorcio.pk]))
        self.assertEqual(respuesta.status_code, 200)

    def test_crear_uf_sin_consorcio(self):
        respuesta = self.client.get(reverse('crear_unidad_funcional'))
        self.assertEqual(respuesta.status_code, 200)

    def test_crear_uf_desde_un_consorcio_ajeno(self):
        respuesta = self.client.get(reverse('crear_unidad_funcional', args=[self.otro.pk]))
        self.assertRedirects(respuesta, reverse('listar_consorcios'), fetch_redirect_response=False)

    def test_gestionar_uf_inexistente_da_404(self):
        respuesta = self.client.get(reverse('gestionar_unidad_funcional', args=[999999]))
        self.assertEqual(respuesta.status_code, 404)

    def test_gestionar_personal_inexistente_da_404(self):
        respuesta = self.client.get(reverse('gestionar_personal', args=[999999]))
        self.assertEqual(respuesta.status_code, 404)

    def test_agregar_personal_a_consorcio_inexistente_da_404(self):
        respuesta = self.client.get(reverse('crear_personal', args=[999999]))
        self.assertEqual(respuesta.status_code, 404)

    def test_configurar_columnas_con_id_no_numerico(self):
        respuesta = self.client.get(reverse('configurar_columnas'), {'consorcio': 'abc'})
        self.assertRedirects(respuesta, reverse('configurar_columnas'), fetch_redirect_response=False)


class UsuarioSinRegistroDeAdministradorTests(TestCase):
    """Usuario con los permisos del grupo pero sin fila en Administrador: no debe dar 500."""

    def setUp(self):
        self.consorcio = crear_consorcio()
        self.personal = Personal.objects.create(
            consorcio=self.consorcio, nombre='Ana', apellido='Paz', dni='30111222', cargo='Encargada')
        usuario, _ = crear_usuario_administrador('sin_registro', con_registro=False)
        self.client.force_login(usuario)

    def assertSinPermiso(self, url):
        respuesta = self.client.get(url)
        self.assertRedirects(respuesta, reverse('listar_consorcios'), fetch_redirect_response=False)

    def test_gestionar_consorcio(self):
        self.assertSinPermiso(reverse('gestionar_consorcio', args=[self.consorcio.pk]))

    def test_definir_alicuotas(self):
        self.assertSinPermiso(reverse('definir_alicuotas', args=[self.consorcio.pk]))

    def test_crear_personal(self):
        self.assertSinPermiso(reverse('crear_personal', args=[self.consorcio.pk]))

    def test_gestionar_personal(self):
        self.assertSinPermiso(reverse('gestionar_personal', args=[self.personal.pk]))

    def test_listar_personal_no_muestra_nada(self):
        respuesta = self.client.get(reverse('listar_personal', args=[self.consorcio.pk]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, 'Paz')


class ListarUnidadesFuncionalesTests(TestCase):
    def setUp(self):
        self.consorcio = crear_consorcio()
        self.otro = crear_consorcio('Torre Dos', '30798765432')
        grupo, _ = Group.objects.get_or_create(name=GRUPO_PROPIETARIOS)
        grupo.permissions.set(Permission.objects.filter(codename__in=PERMISOS_PROPIETARIOS))
        self.propietario_usuario = User.objects.create_user('prop', password='clave')
        self.propietario_usuario.groups.add(grupo)
        propietario = Propietario.objects.create(usuario=self.propietario_usuario)
        UnidadFuncional.objects.create(propietario=propietario, consorcio=self.consorcio, piso=1, departamento='A')
        UnidadFuncional.objects.create(propietario=propietario, consorcio=self.otro, piso=9, departamento='Z')
        vecino = Propietario.objects.create(usuario=User.objects.create_user('vecino', password='clave'))
        UnidadFuncional.objects.create(propietario=vecino, consorcio=self.consorcio, piso=2, departamento='B')

    def unidades_listadas(self):
        respuesta = self.client.get(reverse('listar_unidades_funcionales'))
        self.assertEqual(respuesta.status_code, 200)
        return list(respuesta.context['table'].data)

    def test_propietario_solo_ve_sus_unidades(self):
        self.client.force_login(self.propietario_usuario)
        unidades = self.unidades_listadas()
        self.assertEqual(sorted(uf.departamento for uf in unidades), ['A', 'Z'])

    def test_administrador_solo_ve_las_de_sus_consorcios(self):
        usuario, administrador = crear_usuario_administrador('admin')
        administrador.consorcios.add(self.consorcio)
        self.client.force_login(usuario)
        self.assertEqual({uf.consorcio for uf in self.unidades_listadas()}, {self.consorcio})
