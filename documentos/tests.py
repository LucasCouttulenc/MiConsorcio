import shutil
import tempfile
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from consorcios.models import Consorcio, UnidadFuncional
from usuarios.models import Propietario

from .models import DocumentoConsorcio

MEDIA_PRUEBAS = tempfile.mkdtemp()


def crear_consorcio(nombre, cuit):
    return Consorcio.objects.create(
        nombre=nombre, cuit=cuit, fecha_creacion=date(2020, 1, 1),
        calle='Av. Siempre Viva', altura=742, codigo_postal=1000)


def pdf(nombre='doc.pdf'):
    return SimpleUploadedFile(nombre, b'%PDF-1.4 prueba', content_type='application/pdf')


@override_settings(MEDIA_ROOT=MEDIA_PRUEBAS)
class DocumentosTests(TestCase):
    """Story 8: el admin sube documentos y el propietario los ve con su vencimiento."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_PRUEBAS, ignore_errors=True)

    def setUp(self):
        self.consorcio = crear_consorcio('Torre Uno', '30712345678')
        self.otro_consorcio = crear_consorcio('Torre Dos', '30712345679')
        self.usuario = User.objects.create_user('prop', password='clave')
        UnidadFuncional.objects.create(
            propietario=Propietario.objects.create(usuario=self.usuario), consorcio=self.consorcio,
            piso=3, departamento='B', alicuota=Decimal('50'))
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'clave')

    def subir(self, **datos):
        self.client.force_login(self.admin)
        datos = {'consorcio': self.consorcio.pk, 'tipo': 'certificado', 'titulo': 'Certificado de ascensores',
                 'archivo': pdf(), **datos}
        return self.client.post(reverse('documentos_consorcio'), datos)

    def test_admin_sube_y_propietario_lo_ve(self):
        self.subir(vencimiento='2030-11-30')
        documento = DocumentoConsorcio.objects.get()
        self.assertEqual(documento.consorcio, self.consorcio)
        self.client.force_login(self.usuario)
        respuesta = self.client.get(reverse('mis_documentos'))
        self.assertContains(respuesta, 'Certificado de ascensores')
        self.assertContains(respuesta, 'Vigente hasta 30/11/2030')

    def test_no_acepta_otros_formatos(self):
        self.subir(archivo=SimpleUploadedFile('virus.exe', b'MZ', content_type='application/octet-stream'))
        self.assertFalse(DocumentoConsorcio.objects.exists())

    def test_estado_de_vencimiento(self):
        hoy = date.today()
        documento = DocumentoConsorcio(consorcio=self.consorcio, tipo='poliza', titulo='Póliza')
        self.assertIsNone(documento.estado_vencimiento)
        documento.vencimiento = hoy - timedelta(days=1)
        self.assertEqual(documento.estado_vencimiento, 'vencido')
        documento.vencimiento = hoy + timedelta(days=10)
        self.assertEqual(documento.estado_vencimiento, 'por_vencer')
        documento.vencimiento = hoy + timedelta(days=90)
        self.assertEqual(documento.estado_vencimiento, 'vigente')

    def test_propietario_solo_ve_los_de_sus_consorcios(self):
        DocumentoConsorcio.objects.create(consorcio=self.otro_consorcio, tipo='reglamento',
                                          titulo='Reglamento Torre Dos', archivo=pdf())
        self.client.force_login(self.usuario)
        self.assertNotContains(self.client.get(reverse('mis_documentos')), 'Reglamento Torre Dos')

    def test_admin_borra_documento(self):
        self.subir()
        documento = DocumentoConsorcio.objects.get()
        self.client.post(reverse('borrar_documento', args=[documento.pk]))
        self.assertFalse(DocumentoConsorcio.objects.exists())

    def test_propietario_no_entra_a_la_carga(self):
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(reverse('documentos_consorcio')).status_code, 403)
