from datetime import date, timedelta

from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase
from django.urls import reverse

from config.comun import GRUPO_ADMINISTRADORES, PERMISOS_ADMINISTRADORES
from consorcios.models import Consorcio
from usuarios.models import Administrador

from .models import AsignacionProveedor, EstadoObra, Obra, Proveedor


def crear_consorcio(nombre, cuit):
    return Consorcio.objects.create(
        nombre=nombre, cuit=cuit, fecha_creacion=date(2020, 1, 1),
        calle='Av. Siempre Viva', altura=742, codigo_postal=1000,
    )


def crear_administrador(username, *consorcios):
    grupo, _ = Group.objects.get_or_create(name=GRUPO_ADMINISTRADORES)
    grupo.permissions.set(Permission.objects.filter(codename__in=PERMISOS_ADMINISTRADORES))
    usuario = User.objects.create_user(username, password='clave')
    usuario.groups.add(grupo)
    Administrador.objects.create(usuario=usuario).consorcios.add(*consorcios)
    return usuario


class ObrasTests(TestCase):
    def setUp(self):
        self.consorcio = crear_consorcio('Torre Uno', '30712345678')
        self.otro = crear_consorcio('Torre Dos', '30798765432')
        self.ajeno = crear_consorcio('Torre Ajena', '30711111111')
        self.usuario = crear_administrador('admin', self.consorcio, self.otro)
        self.client.force_login(self.usuario)
        self.activar(self.consorcio)

    def activar(self, consorcio):
        sesion = self.client.session
        sesion['consorcio_activo_id'] = consorcio.pk
        sesion.save()

    def datos_obra(self, **cambios):
        datos = {'concepto': 'Impermeabilización', 'estado': EstadoObra.PLANIFICADA,
                 'fecha_inicio': '2026-11-01', 'fecha_fin_estimada': '2026-12-15', 'descripcion': ''}
        datos.update(cambios)
        return datos

    def obra(self, consorcio=None, **cambios):
        return Obra.objects.create(
            consorcio=consorcio or self.consorcio, concepto='Pintura',
            fecha_inicio=date(2026, 11, 1), fecha_fin_estimada=date(2026, 12, 1), **cambios)

    def test_registrar_obra_en_el_consorcio_activo(self):
        respuesta = self.client.post(reverse('crear_obra'), self.datos_obra())
        self.assertRedirects(respuesta, reverse('listar_obras'), fetch_redirect_response=False)
        self.assertEqual(Obra.objects.get().consorcio, self.consorcio)

    def test_fecha_de_inicio_posterior_a_la_de_fin_se_rechaza(self):
        self.client.post(reverse('crear_obra'), self.datos_obra(fecha_inicio='2026-12-20', fecha_fin_estimada='2026-12-15'))
        self.assertFalse(Obra.objects.exists())

    def test_fecha_de_inicio_anterior_a_hoy_se_acepta(self):
        inicio = (date.today() - timedelta(days=10)).isoformat()
        self.client.post(reverse('crear_obra'), self.datos_obra(fecha_inicio=inicio, estado=EstadoObra.EN_CURSO))
        self.assertTrue(Obra.objects.exists())

    def test_listado_solo_muestra_obras_del_consorcio_activo(self):
        Obra.objects.create(consorcio=self.consorcio, concepto='Terraza', fecha_inicio=date(2026, 1, 1), fecha_fin_estimada=date(2026, 2, 1))
        Obra.objects.create(consorcio=self.otro, concepto='Ascensor', fecha_inicio=date(2026, 1, 1), fecha_fin_estimada=date(2026, 2, 1))
        respuesta = self.client.get(reverse('listar_obras'))
        self.assertEqual([o.concepto for o in respuesta.context['table'].data], ['Terraza'])

    def test_actualizar_estado_de_la_obra(self):
        obra = self.obra()
        self.client.post(reverse('gestionar_obra', args=[obra.pk]), self.datos_obra(concepto='Pintura', estado=EstadoObra.FINALIZADA))
        obra.refresh_from_db()
        self.assertEqual(obra.estado, EstadoObra.FINALIZADA)

    def test_no_puede_gestionar_obras_de_consorcios_que_no_administra(self):
        obra = self.obra(consorcio=self.ajeno)
        self.assertEqual(self.client.get(reverse('gestionar_obra', args=[obra.pk])).status_code, 404)

    def test_asignar_proveedor_con_su_tarea(self):
        obra = self.obra()
        proveedor = Proveedor.objects.create(creado_por=self.usuario, nombre='Pinturas Gómez')
        self.client.post(reverse('asignar_proveedor', args=[obra.pk]), {'proveedor': proveedor.pk, 'tarea': 'Pintura de palier'})
        asignacion = AsignacionProveedor.objects.get()
        self.assertEqual((asignacion.obra, asignacion.proveedor, asignacion.tarea), (obra, proveedor, 'Pintura de palier'))

    def test_un_proveedor_puede_trabajar_en_distintos_consorcios(self):
        proveedor = Proveedor.objects.create(creado_por=self.usuario, nombre='Pinturas Gómez')
        for consorcio in (self.consorcio, self.otro):
            obra = self.obra(consorcio=consorcio)
            self.client.post(reverse('asignar_proveedor', args=[obra.pk]), {'proveedor': proveedor.pk, 'tarea': 'Pintura'})
        self.assertEqual(proveedor.obras.count(), 2)

    def test_no_se_asigna_dos_veces_el_mismo_proveedor(self):
        obra = self.obra()
        proveedor = Proveedor.objects.create(creado_por=self.usuario, nombre='Pinturas Gómez')
        for _ in range(2):
            self.client.post(reverse('asignar_proveedor', args=[obra.pk]), {'proveedor': proveedor.pk, 'tarea': 'Pintura'})
        self.assertEqual(AsignacionProveedor.objects.count(), 1)

    def test_no_puede_asignar_proveedores_de_otro_administrador(self):
        obra = self.obra()
        otro_admin = crear_administrador('otro_admin', self.ajeno)
        proveedor = Proveedor.objects.create(creado_por=otro_admin, nombre='Ajeno')
        self.client.post(reverse('asignar_proveedor', args=[obra.pk]), {'proveedor': proveedor.pk, 'tarea': 'X'})
        self.assertFalse(AsignacionProveedor.objects.exists())

    def test_quitar_proveedor_de_la_obra(self):
        obra = self.obra()
        proveedor = Proveedor.objects.create(creado_por=self.usuario, nombre='Pinturas Gómez')
        asignacion = AsignacionProveedor.objects.create(obra=obra, proveedor=proveedor, tarea='Pintura')
        self.client.post(reverse('quitar_asignacion', args=[asignacion.pk]))
        self.assertFalse(AsignacionProveedor.objects.exists())


class ProveedoresTests(TestCase):
    def setUp(self):
        self.usuario = crear_administrador('admin')
        self.client.force_login(self.usuario)

    def test_registrar_proveedor(self):
        respuesta = self.client.post(reverse('crear_proveedor'), {
            'nombre': 'Ascensores Delta', 'razon_social': 'Delta S.A.', 'telefono': '1148902211', 'email': 'a@delta.com'})
        self.assertRedirects(respuesta, reverse('listar_proveedores'), fetch_redirect_response=False)
        self.assertEqual(Proveedor.objects.get().creado_por, self.usuario)

    def test_solo_ve_y_gestiona_sus_proveedores(self):
        Proveedor.objects.create(creado_por=self.usuario, nombre='Propio')
        ajeno = Proveedor.objects.create(creado_por=crear_administrador('otro'), nombre='Ajeno')
        respuesta = self.client.get(reverse('listar_proveedores'))
        self.assertEqual([p.nombre for p in respuesta.context['table'].data], ['Propio'])
        self.assertEqual(self.client.get(reverse('gestionar_proveedor', args=[ajeno.pk])).status_code, 404)
