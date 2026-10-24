from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from consorcios.models import Consorcio, UnidadFuncional
from usuarios.models import Propietario

from .models import Consulta, EstadoConsulta


def crear_uf(usuario, consorcio, piso=3):
    return UnidadFuncional.objects.create(
        propietario=Propietario.objects.create(usuario=usuario), consorcio=consorcio,
        piso=piso, departamento='B', alicuota=Decimal('50'))


class ConsultasTests(TestCase):
    """Stories 10 y 11: el propietario consulta por la plataforma y sigue las respuestas."""

    def setUp(self):
        self.consorcio = Consorcio.objects.create(
            nombre='Torre Uno', cuit='30712345678', fecha_creacion=date(2020, 1, 1),
            calle='Av. Siempre Viva', altura=742, codigo_postal=1000)
        self.usuario = User.objects.create_user('prop', password='clave')
        self.uf = crear_uf(self.usuario, self.consorcio)
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'clave')

    def crear_consulta(self):
        self.client.force_login(self.usuario)
        self.client.post(reverse('nueva_consulta'), {
            'unidad_funcional': self.uf.pk, 'asunto': 'Pérdida de agua en el techo del 3°B',
            'descripcion': 'Gotea desde ayer en el baño.',
        })
        return Consulta.objects.get()

    def test_crear_consulta_queda_abierta_con_la_descripcion(self):
        consulta = self.crear_consulta()
        self.assertEqual(consulta.estado, EstadoConsulta.ABIERTA)
        self.assertEqual(consulta.mensajes.get().texto, 'Gotea desde ayer en el baño.')
        self.assertContains(self.client.get(reverse('mis_consultas')), 'Pérdida de agua en el techo del 3°B')

    def test_respuesta_del_admin_pasa_a_en_curso(self):
        consulta = self.crear_consulta()
        self.client.force_login(self.admin)
        self.client.post(reverse('gestionar_consulta', args=[consulta.pk]),
                         {'accion': 'responder', 'texto': 'Mandamos al plomero el jueves'})
        consulta.refresh_from_db()
        self.assertEqual(consulta.estado, EstadoConsulta.EN_CURSO)
        self.client.force_login(self.usuario)
        self.assertContains(self.client.get(reverse('ver_consulta', args=[consulta.pk])), 'Mandamos al plomero el jueves')

    def test_consulta_cerrada_no_admite_respuestas(self):
        consulta = self.crear_consulta()
        self.client.force_login(self.admin)
        self.client.post(reverse('gestionar_consulta', args=[consulta.pk]), {'accion': 'cerrar'})
        consulta.refresh_from_db()
        self.assertEqual(consulta.estado, EstadoConsulta.CERRADA)
        self.client.force_login(self.usuario)
        self.client.post(reverse('ver_consulta', args=[consulta.pk]), {'texto': 'Sigue goteando'})
        self.assertEqual(consulta.mensajes.count(), 1)

    def test_propietario_solo_ve_sus_consultas_y_unidades(self):
        consulta = self.crear_consulta()
        otro = User.objects.create_user('otro', password='clave')
        uf_ajena = crear_uf(otro, self.consorcio, piso=1)
        self.client.force_login(otro)
        self.assertEqual(self.client.get(reverse('ver_consulta', args=[consulta.pk])).status_code, 404)
        self.client.post(reverse('nueva_consulta'), {
            'unidad_funcional': self.uf.pk, 'asunto': 'Intento', 'descripcion': 'En una UF que no es mía',
        })
        self.assertEqual(Consulta.objects.count(), 1)
        self.assertNotEqual(uf_ajena.pk, self.uf.pk)

    def test_bandeja_del_admin_filtra_por_estado(self):
        consulta = self.crear_consulta()
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse('bandeja_consultas')), consulta.asunto)
        self.assertNotContains(self.client.get(reverse('bandeja_consultas'), {'estado': 'cerrada'}), consulta.asunto)

    def test_propietario_no_entra_a_la_bandeja_del_admin(self):
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(reverse('bandeja_consultas')).status_code, 403)
