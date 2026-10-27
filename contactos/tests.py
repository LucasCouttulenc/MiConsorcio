from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from consorcios.models import Consorcio, UnidadFuncional
from usuarios.models import Propietario

from .models import ContactoAdministracion, TelefonoUtil


def crear_consorcio(nombre, cuit):
    return Consorcio.objects.create(
        nombre=nombre, cuit=cuit, fecha_creacion=date(2020, 1, 1),
        calle='Av. Siempre Viva', altura=742, codigo_postal=1000)


class TelefonosDeContactoTests(TestCase):
    """El admin carga el contacto de la administración y los teléfonos útiles; el propietario los ve."""

    def setUp(self):
        self.consorcio = crear_consorcio('Torre Uno', '30712345678')
        self.otro_consorcio = crear_consorcio('Torre Dos', '30712345679')
        self.usuario = User.objects.create_user('prop', password='clave')
        UnidadFuncional.objects.create(
            propietario=Propietario.objects.create(usuario=self.usuario), consorcio=self.consorcio,
            piso=3, departamento='B', alicuota=Decimal('50'))
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'clave')

    def como_admin(self, consorcio=None):
        self.client.force_login(self.admin)
        self.client.post(reverse('cambiar_consorcio_activo'), {'consorcio_id': (consorcio or self.consorcio).pk})

    def guardar_contacto(self, **datos):
        datos = {'accion': 'contacto', **{f'contacto-{campo}': valor for campo, valor in datos.items()}}
        return self.client.post(reverse('contactos_consorcio'), datos)

    def agregar_telefono(self, **datos):
        datos = {'accion': 'telefono', **{f'telefono-{campo}': valor for campo, valor in datos.items()}}
        return self.client.post(reverse('contactos_consorcio'), datos)

    def test_todos_los_campos_de_la_administracion_son_opcionales(self):
        self.como_admin()
        respuesta = self.guardar_contacto()
        self.assertRedirects(respuesta, reverse('contactos_consorcio'))
        self.assertTrue(ContactoAdministracion.objects.get(consorcio=self.consorcio).esta_vacio)

    def test_el_propietario_solo_ve_los_campos_cargados(self):
        self.como_admin()
        self.guardar_contacto(nombre='Administración de prueba', telefono='1111-2222')
        self.client.force_login(self.usuario)
        respuesta = self.client.get(reverse('mis_contactos'))
        self.assertContains(respuesta, 'Administración de prueba')
        self.assertContains(respuesta, 'href="tel:1111-2222"')
        self.assertNotContains(respuesta, 'Horario de atención')
        self.assertNotContains(respuesta, 'Sitio web')

    def test_email_invalido_no_se_guarda(self):
        self.como_admin()
        respuesta = self.guardar_contacto(email='no-es-un-mail')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(ContactoAdministracion.objects.get(consorcio=self.consorcio).email, '')

    def test_telefono_util_pide_nombre_y_telefono(self):
        self.como_admin()
        self.agregar_telefono(nombre='Ascensores', telefono='', detalle='Urgencias')
        self.assertFalse(TelefonoUtil.objects.exists())
        self.agregar_telefono(nombre='Ascensores', telefono='4555-8800', detalle='')
        self.assertEqual(TelefonoUtil.objects.get().consorcio, self.consorcio)

    def test_admin_borra_telefono_solo_de_su_consorcio_activo(self):
        ajeno = TelefonoUtil.objects.create(consorcio=self.otro_consorcio, nombre='Gas', telefono='0800')
        self.como_admin()
        respuesta = self.client.post(reverse('borrar_telefono', args=[ajeno.pk]))
        self.assertEqual(respuesta.status_code, 404)
        self.assertTrue(TelefonoUtil.objects.filter(pk=ajeno.pk).exists())

    def test_sin_datos_el_propietario_ve_sin_informacion(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.get(reverse('mis_contactos'))
        self.assertContains(respuesta, 'Sin información')

    def test_el_propietario_no_ve_contactos_de_otros_consorcios(self):
        TelefonoUtil.objects.create(consorcio=self.otro_consorcio, nombre='Cerrajería ajena', telefono='1234')
        self.client.force_login(self.usuario)
        respuesta = self.client.get(reverse('mis_contactos'))
        self.assertNotContains(respuesta, 'Cerrajería ajena')

    def test_el_propietario_no_entra_a_la_pantalla_del_admin(self):
        self.client.force_login(self.usuario)
        respuesta = self.client.get(reverse('contactos_consorcio'))
        self.assertEqual(respuesta.status_code, 403)
