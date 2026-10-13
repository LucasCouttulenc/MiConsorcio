import json
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from consorcios.models import Consorcio, GrupoProrrateo, Rubro, UnidadFuncional
from usuarios.models import Propietario

from .forms import FormularioServicioRecurrente
from .models import Gasto, Liquidacion, ServicioRecurrente


def crear_consorcio(nombre='Torre Uno', cuit='30712345678'):
    consorcio = Consorcio.objects.create(
        nombre=nombre, cuit=cuit, fecha_creacion=date(2020, 1, 1),
        calle='Av. Siempre Viva', altura=742, codigo_postal=1000,
    )
    rubro = Rubro.objects.create(consorcio=consorcio, nombre='SERVICIOS')
    columna = GrupoProrrateo.objects.create(consorcio=consorcio, rubro=rubro, nombre='General', codigo='A')
    return consorcio, columna


class ServicioRecurrenteModeloTests(TestCase):
    def setUp(self):
        self.consorcio, self.columna = crear_consorcio()

    def servicio(self, **kwargs):
        datos = {'consorcio': self.consorcio, 'columna': self.columna, 'concepto': 'Fumigación',
                 'frecuencia_meses': 3, 'periodo_inicio': '2026-01'}
        datos.update(kwargs)
        return ServicioRecurrente(**datos)

    def test_trimestral_corresponde_cada_tres_meses(self):
        servicio = self.servicio()
        corresponden = [m for m in range(1, 13) if servicio.corresponde_en(f'2026-{m:02d}')]
        self.assertEqual(corresponden, [1, 4, 7, 10])

    def test_cruza_el_cambio_de_anio(self):
        servicio = self.servicio(periodo_inicio='2026-11', frecuencia_meses=2)
        self.assertTrue(servicio.corresponde_en('2027-01'))
        self.assertFalse(servicio.corresponde_en('2026-12'))

    def test_no_corresponde_antes_del_inicio(self):
        self.assertFalse(self.servicio().corresponde_en('2025-10'))

    def test_no_corresponde_despues_del_fin(self):
        servicio = self.servicio(periodo_fin='2026-06')
        self.assertTrue(servicio.corresponde_en('2026-04'))
        self.assertFalse(servicio.corresponde_en('2026-07'))

    def test_pausado_no_corresponde(self):
        self.assertFalse(self.servicio(activo=False).corresponde_en('2026-01'))

    def test_proximo_periodo(self):
        servicio = self.servicio()
        self.assertEqual(servicio.proximo_periodo('2026-02'), '2026-04')
        self.assertEqual(servicio.proximo_periodo('2026-04'), '2026-04')
        self.assertEqual(servicio.proximo_periodo('2025-05'), '2026-01')
        self.assertEqual(servicio.proximo_periodo('2026-11'), '2027-01')
        self.assertIsNone(self.servicio(periodo_fin='2026-06').proximo_periodo('2026-05'))

    def test_rubro_sale_de_la_columna(self):
        self.assertEqual(self.servicio().rubro, self.columna.rubro)


class FormularioServicioRecurrenteTests(TestCase):
    def setUp(self):
        self.consorcio, self.columna = crear_consorcio()
        self.otro, self.columna_ajena = crear_consorcio('Torre Dos', '30798765432')

    def datos(self, **kwargs):
        datos = {'concepto': 'Fumigación', 'columna': self.columna.pk, 'tipo': 'ordinario',
                 'frecuencia_meses': 3, 'periodo_inicio': '2026-01', 'periodo_fin': '', 'monto_sugerido': ''}
        datos.update(kwargs)
        return datos

    def test_monto_sugerido_es_opcional(self):
        formulario = FormularioServicioRecurrente(self.datos(), consorcio=self.consorcio)
        self.assertTrue(formulario.is_valid(), formulario.errors)
        servicio = formulario.save()
        self.assertIsNone(servicio.monto_sugerido)
        self.assertEqual(servicio.consorcio, self.consorcio)

    def test_no_acepta_columna_de_otro_consorcio(self):
        formulario = FormularioServicioRecurrente(self.datos(columna=self.columna_ajena.pk), consorcio=self.consorcio)
        self.assertIn('columna', formulario.errors)

    def test_valida_formato_de_periodo(self):
        formulario = FormularioServicioRecurrente(self.datos(periodo_inicio='2026-13'), consorcio=self.consorcio)
        self.assertIn('periodo_inicio', formulario.errors)

    def test_fin_no_puede_ser_anterior_al_inicio(self):
        formulario = FormularioServicioRecurrente(self.datos(periodo_fin='2025-12'), consorcio=self.consorcio)
        self.assertIn('periodo_fin', formulario.errors)

    def test_monto_tiene_que_ser_positivo(self):
        formulario = FormularioServicioRecurrente(self.datos(monto_sugerido='-5'), consorcio=self.consorcio)
        self.assertIn('monto_sugerido', formulario.errors)


class ServiciosRecurrentesVistasTests(TestCase):
    def setUp(self):
        self.consorcio, self.columna = crear_consorcio()
        self.otro, _ = crear_consorcio('Torre Dos', '30798765432')
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'clave')
        self.client.force_login(self.admin)
        self.url = reverse('servicios_recurrentes')

    def test_crear_pausar_y_borrar(self):
        respuesta = self.client.post(self.url, {
            'consorcio': self.consorcio.pk, 'accion': 'crear', 'concepto': 'Fumigación',
            'columna': self.columna.pk, 'tipo': 'ordinario', 'frecuencia_meses': 3,
            'periodo_inicio': '2026-01', 'periodo_fin': '', 'monto_sugerido': '45000',
        })
        self.assertEqual(respuesta.status_code, 302)
        servicio = ServicioRecurrente.objects.get()
        self.assertEqual(servicio.monto_sugerido, Decimal('45000'))

        self.client.post(self.url, {'consorcio': self.consorcio.pk, 'accion': 'pausar', 'servicio_id': servicio.pk})
        servicio.refresh_from_db()
        self.assertFalse(servicio.activo)

        self.client.post(self.url, {'consorcio': self.consorcio.pk, 'accion': 'borrar', 'servicio_id': servicio.pk})
        self.assertFalse(ServicioRecurrente.objects.exists())

    def test_no_se_puede_tocar_un_servicio_desde_otro_consorcio(self):
        servicio = ServicioRecurrente.objects.create(
            consorcio=self.consorcio, columna=self.columna, concepto='Fumigación', periodo_inicio='2026-01')
        respuesta = self.client.post(self.url, {'consorcio': self.otro.pk, 'accion': 'borrar', 'servicio_id': servicio.pk})
        self.assertEqual(respuesta.status_code, 404)
        self.assertTrue(ServicioRecurrente.objects.exists())

    def test_listado_muestra_el_proximo_periodo(self):
        ServicioRecurrente.objects.create(
            consorcio=self.consorcio, columna=self.columna, concepto='Fumigación', periodo_inicio='2026-01')
        respuesta = self.client.get(self.url, {'consorcio': self.consorcio.pk})
        self.assertContains(respuesta, 'Fumigación')
        self.assertContains(respuesta, date.today().strftime('%Y-%m'))


class ServiciosEnLiquidacionTests(TestCase):
    def setUp(self):
        self.consorcio, self.columna = crear_consorcio()
        for depto in ('A', 'B'):
            usuario = User.objects.create_user(f'prop{depto}', password='clave')
            UnidadFuncional.objects.create(
                propietario=Propietario.objects.create(usuario=usuario), consorcio=self.consorcio,
                piso=1, departamento=depto, alicuota=Decimal('50'))
        self.servicio = ServicioRecurrente.objects.create(
            consorcio=self.consorcio, columna=self.columna, concepto='Fumigación',
            frecuencia_meses=3, periodo_inicio='2026-01')
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'clave')
        self.client.force_login(self.admin)

    def test_generar_pasa_los_servicios_activos(self):
        ServicioRecurrente.objects.create(
            consorcio=self.consorcio, columna=self.columna, concepto='Pausado',
            periodo_inicio='2026-01', activo=False)
        respuesta = self.client.get(reverse('generar_liquidacion'))
        servicios = respuesta.context['servicios_por_consorcio'][self.consorcio.pk]
        self.assertEqual([s['concepto'] for s in servicios], ['Fumigación'])
        self.assertEqual(servicios[0]['monto'], '')
        self.assertEqual(servicios[0]['rubro_id'], self.columna.rubro_id)

    def test_finalizar_guarda_el_servicio_de_origen(self):
        gastos = [
            {'fila': 'gasto-0', 'concepto': 'Fumigación', 'tipo': 'ordinario', 'rubro': self.columna.rubro_id,
             'grupo': self.columna.pk, 'monto': '45000', 'servicio': str(self.servicio.pk)},
            {'fila': 'gasto-1', 'concepto': 'Limpieza', 'tipo': 'ordinario', 'rubro': self.columna.rubro_id,
             'grupo': self.columna.pk, 'monto': '1000'},
        ]
        respuesta = self.client.post(reverse('finalizar_liquidacion'), {
            'consorcio': self.consorcio.pk, 'mes': '4', 'anio': '2026',
            'fecha_cierre': '2026-04-30', 'fecha_vencimiento_1': '2026-05-10',
            'gastos': json.dumps(gastos),
        })
        liquidacion = Liquidacion.objects.get()
        self.assertRedirects(respuesta, reverse('detalle_liquidacion', args=[liquidacion.pk]), fetch_redirect_response=False)
        fumigacion = Gasto.objects.get(concepto='Fumigación')
        self.assertEqual(fumigacion.servicio, self.servicio)
        self.assertIsNone(Gasto.objects.get(concepto='Limpieza').servicio)
        self.assertEqual(list(self.servicio.gastos.all()), [fumigacion])
