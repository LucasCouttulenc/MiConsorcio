import shutil
import tempfile
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from config.comun import GRUPO_ADMINISTRADORES, GRUPO_PROPIETARIOS, PERMISOS_ADMINISTRADORES, PERMISOS_PROPIETARIOS
from consorcios.models import Consorcio, Rubro, UnidadFuncional
from consultas.models import Consulta, EstadoConsulta
from documentos.models import DocumentoConsorcio

from .models import Administrador, Propietario

MEDIA_PRUEBAS = tempfile.mkdtemp()


def crear_consorcio(nombre, cuit):
    return Consorcio.objects.create(
        nombre=nombre, cuit=cuit, fecha_creacion=date(2020, 1, 1),
        calle='Av. Siempre Viva', altura=742, codigo_postal=1000)


def crear_usuario(username, grupo, permisos):
    grupo, _ = Group.objects.get_or_create(name=grupo)
    grupo.permissions.set(Permission.objects.filter(codename__in=permisos))
    usuario = User.objects.create_user(username, password='clave')
    usuario.groups.add(grupo)
    return usuario


def consorcio_en_sesion(client):
    return client.session.get('consorcio_activo_id')


def forzar_consorcio_en_sesion(client, consorcio_id):
    """Pone un id cualquiera en la sesión, como si se hubiera manipulado sin pasar por el selector."""
    sesion = client.session
    sesion['consorcio_activo_id'] = consorcio_id
    sesion.save()


@override_settings(MEDIA_ROOT=MEDIA_PRUEBAS)
class ConsorcioActivoTests(TestCase):
    """Nadie puede operar sobre un consorcio que no administra cambiando el consorcio activo de la sesión."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_PRUEBAS, ignore_errors=True)

    def setUp(self):
        self.propio = crear_consorcio('Torre Uno', '30712345678')
        self.segundo = crear_consorcio('Torre Zeta', '30712345670')
        self.ajeno = crear_consorcio('Torre Dos', '30712345679')

        self.admin = crear_usuario('admin', GRUPO_ADMINISTRADORES, PERMISOS_ADMINISTRADORES)
        Administrador.objects.create(usuario=self.admin).consorcios.add(self.propio, self.segundo)

        # Los propietarios reales tienen view_consorcio, que es el permiso que piden las vistas de administración.
        self.propietario = crear_usuario('prop', GRUPO_PROPIETARIOS, PERMISOS_PROPIETARIOS)
        UnidadFuncional.objects.create(
            propietario=Propietario.objects.create(usuario=self.propietario), consorcio=self.propio,
            piso=1, departamento='A', alicuota=Decimal('50'))

        vecino = Propietario.objects.create(usuario=User.objects.create_user('vecino', password='clave'))
        uf_ajena = UnidadFuncional.objects.create(
            propietario=vecino, consorcio=self.ajeno, piso=2, departamento='B', alicuota=Decimal('50'))
        self.consulta_ajena = Consulta.objects.create(unidad_funcional=uf_ajena, asunto='Filtración en Torre Dos')
        self.documento_ajeno = DocumentoConsorcio.objects.create(
            consorcio=self.ajeno, tipo='reglamento', titulo='Reglamento Torre Dos',
            archivo=SimpleUploadedFile('reglamento.pdf', b'%PDF-1.4', content_type='application/pdf'))

    def assertSinTocarElAjeno(self):
        self.assertTrue(DocumentoConsorcio.objects.filter(pk=self.documento_ajeno.pk).exists())
        self.consulta_ajena.refresh_from_db()
        self.assertEqual(self.consulta_ajena.estado, EstadoConsulta.ABIERTA)
        self.assertEqual(self.consulta_ajena.mensajes.count(), 0)
        self.assertFalse(Rubro.objects.filter(consorcio=self.ajeno).exists())

    def intentar_operar_sobre_el_ajeno(self):
        """Respuestas de las vistas de administración con el consorcio ajeno forzado en la sesión."""
        respuestas = {}
        for nombre, metodo, url, datos in (
            ('morosidad', 'get', reverse('morosidad'), {}),
            ('bandeja', 'get', reverse('bandeja_consultas'), {'estado': 'todas'}),
            ('columnas', 'post', reverse('configurar_columnas'), {'accion': 'crear_rubro', 'nombre_rubro': 'INTRUSO'}),
            ('borrar_documento', 'post', reverse('borrar_documento', args=[self.documento_ajeno.pk]), {}),
            ('responder', 'post', reverse('gestionar_consulta', args=[self.consulta_ajena.pk]),
             {'accion': 'responder', 'texto': 'Respuesta falsa'}),
            ('cerrar', 'post', reverse('gestionar_consulta', args=[self.consulta_ajena.pk]), {'accion': 'cerrar'}),
        ):
            forzar_consorcio_en_sesion(self.client, self.ajeno.pk)
            respuestas[nombre] = getattr(self.client, metodo)(url, datos)
        return respuestas

    # Selector del sidebar

    def test_cambiar_a_otro_consorcio_propio(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('cambiar_consorcio_activo'), {'consorcio_id': self.segundo.pk})
        self.assertEqual(consorcio_en_sesion(self.client), self.segundo.pk)

    def test_no_se_puede_cambiar_a_un_consorcio_ajeno(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('cambiar_consorcio_activo'), {'consorcio_id': self.propio.pk})
        self.client.post(reverse('cambiar_consorcio_activo'), {'consorcio_id': self.ajeno.pk})
        self.assertEqual(consorcio_en_sesion(self.client), self.propio.pk)

    def test_propietario_no_puede_elegir_ningun_consorcio(self):
        self.client.force_login(self.propietario)
        self.client.post(reverse('cambiar_consorcio_activo'), {'consorcio_id': self.ajeno.pk})
        self.assertIsNone(consorcio_en_sesion(self.client))

    def test_id_no_numerico_no_se_guarda(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('cambiar_consorcio_activo'), {'consorcio_id': 'abc'})
        self.assertNotEqual(consorcio_en_sesion(self.client), 'abc')

    def test_no_acepta_get(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get(reverse('cambiar_consorcio_activo'), {'consorcio_id': self.ajeno.pk})
        self.assertEqual(respuesta.status_code, 405)

    def test_next_externo_redirige_a_bienvenida(self):
        self.client.force_login(self.admin)
        respuesta = self.client.post(reverse('cambiar_consorcio_activo'), {
            'consorcio_id': self.propio.pk, 'next': 'https://evil.example/robar'})
        self.assertRedirects(respuesta, reverse('bienvenida'), fetch_redirect_response=False)

    def test_next_interno_se_respeta(self):
        self.client.force_login(self.admin)
        respuesta = self.client.post(reverse('cambiar_consorcio_activo'), {
            'consorcio_id': self.propio.pk, 'next': reverse('morosidad')})
        self.assertRedirects(respuesta, reverse('morosidad'), fetch_redirect_response=False)

    # Sesión manipulada

    def test_id_invalido_en_sesion_no_rompe_las_paginas(self):
        self.client.force_login(self.admin)
        forzar_consorcio_en_sesion(self.client, 'abc')
        self.assertEqual(self.client.get(reverse('bienvenida')).status_code, 200)
        self.assertEqual(consorcio_en_sesion(self.client), self.propio.pk)

    def test_administrador_con_consorcio_ajeno_en_sesion_trabaja_sobre_el_suyo(self):
        self.client.force_login(self.admin)
        respuestas = self.intentar_operar_sobre_el_ajeno()
        self.assertEqual(respuestas['morosidad'].context['consorcio'], self.propio)
        self.assertNotContains(respuestas['bandeja'], 'Filtración en Torre Dos')
        self.assertEqual(respuestas['borrar_documento'].status_code, 404)
        self.assertEqual(respuestas['responder'].status_code, 404)
        self.assertEqual(respuestas['cerrar'].status_code, 404)
        self.assertTrue(Rubro.objects.filter(consorcio=self.propio, nombre='INTRUSO').exists())
        self.assertSinTocarElAjeno()

    def test_propietario_con_consorcio_ajeno_en_sesion_no_ve_ni_toca_nada(self):
        self.client.force_login(self.propietario)
        respuestas = self.intentar_operar_sobre_el_ajeno()
        for nombre, respuesta in respuestas.items():
            with self.subTest(vista=nombre):
                self.assertRedirects(respuesta, reverse('bienvenida'), fetch_redirect_response=False)
        self.assertSinTocarElAjeno()


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class InvitacionPropietarioTests(TestCase):
    """El link de invitación crea la cuenta del propietario o, si ya existe, pide su contraseña."""

    def setUp(self):
        from django.test import RequestFactory
        from usuarios.invitaciones import enviar_invitacion_propietario
        self.consorcio = crear_consorcio('Torre Uno', '30712345678')
        self.unidad = UnidadFuncional.objects.create(consorcio=self.consorcio, piso=1, departamento='A')
        self.request = RequestFactory().get('/')
        self.enviar = enviar_invitacion_propietario

    def url_invitacion(self, email):
        import re
        from django.core import mail
        self.enviar(self.unidad, email, self.request)
        return re.search(r'(/invitacion/propietario/[^/\s]+/)', mail.outbox[-1].body).group(1)

    def test_cuenta_nueva_se_crea_con_contrasena_valida(self):
        url = self.url_invitacion('nuevo@correo.com')
        datos = {'nombre': 'Ana', 'apellido': 'Paz', 'password': 'Edificio-2026', 'confirmar_password': 'Edificio-2026'}
        respuesta = self.client.post(url, datos)
        self.assertRedirects(respuesta, reverse('inicio_propietario'), fetch_redirect_response=False)
        self.unidad.refresh_from_db()
        self.assertEqual(self.unidad.propietario.usuario.username, 'nuevo@correo.com')
        self.assertTrue(self.unidad.propietario.usuario.check_password('Edificio-2026'))

    def test_cuenta_nueva_rechaza_contrasena_debil(self):
        url = self.url_invitacion('nuevo@correo.com')
        respuesta = self.client.post(url, {'nombre': 'Ana', 'apellido': 'Paz', 'password': '1', 'confirmar_password': '1'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(User.objects.filter(username='nuevo@correo.com').exists())
        self.unidad.refresh_from_db()
        self.assertIsNone(self.unidad.propietario_id)

    def test_cuenta_existente_no_entra_con_solo_abrir_el_link(self):
        User.objects.create_user('vecina@correo.com', email='vecina@correo.com', password='clave-vieja-123')
        url = self.url_invitacion('vecina@correo.com')
        respuesta = self.client.get(url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.context['cuenta_existente'])
        self.assertNotIn('_auth_user_id', self.client.session)
        self.unidad.refresh_from_db()
        self.assertIsNone(self.unidad.propietario_id)

    def test_cuenta_existente_con_contrasena_incorrecta_no_vincula(self):
        User.objects.create_user('vecina@correo.com', email='vecina@correo.com', password='clave-vieja-123')
        url = self.url_invitacion('vecina@correo.com')
        self.client.post(url, {'password': 'otra'})
        self.assertNotIn('_auth_user_id', self.client.session)
        self.unidad.refresh_from_db()
        self.assertIsNone(self.unidad.propietario_id)

    def test_cuenta_existente_con_su_contrasena_suma_la_unidad(self):
        usuario = User.objects.create_user('vecina@correo.com', email='vecina@correo.com', password='clave-vieja-123')
        url = self.url_invitacion('vecina@correo.com')
        respuesta = self.client.post(url, {'password': 'clave-vieja-123'})
        self.assertRedirects(respuesta, reverse('inicio_propietario'), fetch_redirect_response=False)
        self.unidad.refresh_from_db()
        self.assertEqual(self.unidad.propietario.usuario, usuario)
        self.assertEqual(int(self.client.session['_auth_user_id']), usuario.pk)

    def test_correo_con_cuenta_suma_la_unidad_directo_sin_mandar_link(self):
        from django.core import mail
        from usuarios.invitaciones import asignar_propietario
        usuario = User.objects.create_user('vecina@correo.com', email='vecina@correo.com', password='clave-vieja-123')
        mail.outbox = []
        self.assertEqual(asignar_propietario(self.unidad, 'Vecina@Correo.com', self.request), 'vinculada')
        self.assertEqual(mail.outbox, [])
        self.unidad.refresh_from_db()
        self.assertEqual(self.unidad.propietario.usuario, usuario)

    def test_correo_sin_cuenta_recibe_el_link(self):
        from django.core import mail
        from usuarios.invitaciones import asignar_propietario
        mail.outbox = []
        self.assertEqual(asignar_propietario(self.unidad, 'nuevo@correo.com', self.request), 'invitada')
        self.assertEqual(len(mail.outbox), 1)

    def test_al_crear_la_cuenta_se_suman_las_otras_unidades_pendientes(self):
        otra = UnidadFuncional.objects.create(consorcio=self.consorcio, piso=2, departamento='B')
        self.enviar(otra, 'nuevo@correo.com', self.request)
        url = self.url_invitacion('nuevo@correo.com')
        datos = {'nombre': 'Ana', 'apellido': 'Paz', 'password': 'Edificio-2026', 'confirmar_password': 'Edificio-2026'}
        self.client.post(url, datos)
        otra.refresh_from_db()
        self.assertEqual(otra.propietario.usuario.username, 'nuevo@correo.com')

    def test_link_viejo_con_sesion_iniciada_suma_directo(self):
        usuario = User.objects.create_user('vecina@correo.com', email='vecina@correo.com', password='clave-vieja-123')
        url = self.url_invitacion('vecina@correo.com')
        self.client.force_login(usuario)
        respuesta = self.client.get(url)
        self.assertRedirects(respuesta, reverse('inicio_propietario'), fetch_redirect_response=False)
        self.unidad.refresh_from_db()
        self.assertEqual(self.unidad.propietario.usuario, usuario)
