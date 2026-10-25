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


def activar_consorcio(client, consorcio):
    """Elige el consorcio activo igual que el selector del sidebar."""
    return client.post(reverse('cambiar_consorcio_activo'), {'consorcio_id': consorcio.pk})


def forzar_consorcio_en_sesion(client, consorcio_id):
    """Pone un id cualquiera en la sesión, como si se hubiera manipulado sin pasar por el selector."""
    sesion = client.session
    sesion['consorcio_activo_id'] = consorcio_id
    sesion.save()


class PermisosAdministradorTests(TestCase):
    def setUp(self):
        self.consorcio = crear_consorcio()
        self.otro = crear_consorcio('Torre Dos', '30798765432')
        self.usuario, administrador = crear_usuario_administrador('admin')
        administrador.consorcios.add(self.consorcio)
        self.client.force_login(self.usuario)

    def test_crear_uf_sin_consorcio(self):
        respuesta = self.client.get(reverse('crear_unidad_funcional'))
        self.assertEqual(respuesta.status_code, 200)

    def test_crear_uf_en_un_consorcio_ajeno_no_se_guarda(self):
        propietario = Propietario.objects.create(usuario=User.objects.create_user('prop', password='clave'))
        self.client.post(reverse('crear_unidad_funcional'), {
            'propietario': propietario.pk, 'consorcio': self.otro.pk, 'piso': 1, 'departamento': 'A',
        })
        self.assertFalse(UnidadFuncional.objects.filter(consorcio=self.otro).exists())

    def test_gestionar_uf_inexistente_da_404(self):
        respuesta = self.client.get(reverse('gestionar_unidad_funcional', args=[999999]))
        self.assertEqual(respuesta.status_code, 404)

    def test_gestionar_personal_inexistente_da_404(self):
        respuesta = self.client.get(reverse('gestionar_personal', args=[999999]))
        self.assertEqual(respuesta.status_code, 404)

    def test_agregar_personal_va_al_consorcio_activo_aunque_se_mande_otro(self):
        self.client.post(reverse('crear_personal'), {
            'consorcio': self.otro.pk, 'nombre': 'Ana', 'apellido': 'Paz', 'dni': '30111222',
            'cargo': 'Encargada', 'tipo_contratacion': 'directo',
        })
        self.assertFalse(Personal.objects.filter(consorcio=self.otro).exists())
        self.assertTrue(Personal.objects.filter(consorcio=self.consorcio, dni='30111222').exists())

    def test_configurar_columnas_con_id_no_numerico_en_sesion(self):
        forzar_consorcio_en_sesion(self.client, 'abc')
        respuesta = self.client.get(reverse('configurar_columnas'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context['consorcio'], self.consorcio)

    def test_crear_consorcio_muestra_el_formulario(self):
        respuesta = self.client.get(reverse('crear_consorcio'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, reverse('bienvenida'))


class UsuarioSinRegistroDeAdministradorTests(TestCase):
    """Usuario con los permisos del grupo pero sin fila en Administrador: no debe dar 500."""

    def setUp(self):
        self.consorcio = crear_consorcio()
        self.personal = Personal.objects.create(
            consorcio=self.consorcio, nombre='Ana', apellido='Paz', dni='30111222', cargo='Encargada')
        usuario, _ = crear_usuario_administrador('sin_registro', con_registro=False)
        self.client.force_login(usuario)
        forzar_consorcio_en_sesion(self.client, self.consorcio.pk)

    def assertSinPermiso(self, url):
        respuesta = self.client.get(url)
        self.assertRedirects(respuesta, reverse('bienvenida'), fetch_redirect_response=False)

    def test_gestionar_consorcio(self):
        self.assertSinPermiso(reverse('gestionar_consorcio'))

    def test_definir_alicuotas(self):
        self.assertSinPermiso(reverse('definir_alicuotas'))

    def test_crear_personal(self):
        self.assertSinPermiso(reverse('crear_personal'))

    def test_gestionar_personal(self):
        self.assertSinPermiso(reverse('gestionar_personal', args=[self.personal.pk]))

    def test_listar_personal_no_muestra_nada(self):
        respuesta = self.client.get(reverse('listar_personal'))
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

    def test_propietario_no_lista_unidades_aunque_fuerce_el_consorcio(self):
        # El listado es del administrador; el propietario ve sus UF desde su portal.
        self.client.force_login(self.propietario_usuario)
        forzar_consorcio_en_sesion(self.client, self.consorcio.pk)
        self.assertEqual(self.unidades_listadas(), [])

    def test_administrador_solo_ve_las_de_sus_consorcios(self):
        usuario, administrador = crear_usuario_administrador('admin')
        administrador.consorcios.add(self.consorcio)
        self.client.force_login(usuario)
        self.assertEqual({uf.consorcio for uf in self.unidades_listadas()}, {self.consorcio})

    def test_administrador_que_fuerza_otro_consorcio_sigue_viendo_el_suyo(self):
        usuario, administrador = crear_usuario_administrador('admin')
        administrador.consorcios.add(self.consorcio)
        self.client.force_login(usuario)
        forzar_consorcio_en_sesion(self.client, self.otro.pk)
        self.assertEqual({uf.consorcio for uf in self.unidades_listadas()}, {self.consorcio})
