import json
import shutil
import tempfile
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from consorcios.models import Consorcio, GrupoProrrateo, Rubro, UnidadFuncional
from usuarios.models import Propietario

from .forms import FormularioPago, FormularioServicioRecurrente
from .models import DetalleLiquidacionUF, Gasto, ImputacionPago, Liquidacion, Pago, ServicioRecurrente


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


class FinalizarConMontosInvalidosTests(TestCase):
    """Montos armados a mano (NaN, Infinity, enormes) no deben dar 500."""

    def setUp(self):
        self.consorcio, self.columna = crear_consorcio()
        for depto in ('A', 'B'):
            usuario = User.objects.create_user(f'prop{depto}', password='clave')
            UnidadFuncional.objects.create(
                propietario=Propietario.objects.create(usuario=usuario), consorcio=self.consorcio,
                piso=1, departamento=depto, alicuota=Decimal('50'))
        self.client.force_login(User.objects.create_superuser('admin', 'admin@example.com', 'clave'))

    def finalizar(self, monto):
        gastos = [{'fila': 'gasto-0', 'concepto': 'Limpieza', 'tipo': 'ordinario',
                   'grupo': self.columna.pk, 'monto': monto}]
        return self.client.post(reverse('finalizar_liquidacion'), {
            'consorcio': self.consorcio.pk, 'mes': '4', 'anio': '2026',
            'fecha_cierre': '2026-04-30', 'fecha_vencimiento_1': '2026-05-10',
            'gastos': json.dumps(gastos),
        })

    def test_montos_invalidos_se_rechazan_sin_error(self):
        for monto in ('NaN', '-NaN', 'sNaN', 'Infinity', '-Infinity', '1E+20', '10000000000'):
            with self.subTest(monto=monto):
                respuesta = self.finalizar(monto)
                self.assertRedirects(respuesta, reverse('generar_liquidacion'), fetch_redirect_response=False)
        self.assertFalse(Gasto.objects.exists())

    def test_monto_maximo_permitido(self):
        self.finalizar('9999999999.99')
        self.assertTrue(Liquidacion.objects.get().cerrada)


def archivo(nombre='comprobante.pdf', tipo='application/pdf', contenido=b'%PDF-1.4'):
    return SimpleUploadedFile(nombre, contenido, content_type=tipo)


class FormularioPagoTests(TestCase):
    def formulario(self, **cambios):
        datos = {'fecha_pago': date.today().isoformat(), 'monto_pagado': '1000'}
        archivos = {'comprobante': cambios.pop('comprobante', archivo())}
        datos.update(cambios)
        return FormularioPago(datos, archivos)

    def test_pago_valido(self):
        self.assertTrue(self.formulario().is_valid())

    def test_acepta_imagenes(self):
        self.assertTrue(self.formulario(comprobante=archivo('foto.JPG', 'image/jpeg')).is_valid())
        self.assertTrue(self.formulario(comprobante=archivo('foto.png', 'image/png')).is_valid())

    def test_monto_tiene_que_ser_positivo(self):
        for monto in ('-500', '0'):
            with self.subTest(monto=monto):
                self.assertIn('monto_pagado', self.formulario(monto_pagado=monto).errors)

    def test_fecha_no_puede_ser_futura(self):
        manana = (date.today() + timedelta(days=1)).isoformat()
        self.assertIn('fecha_pago', self.formulario(fecha_pago=manana).errors)

    def test_rechaza_html_aunque_diga_ser_pdf(self):
        formulario = self.formulario(comprobante=archivo('xss.html', 'application/pdf', b'<script>alert(1)</script>'))
        self.assertIn('comprobante', formulario.errors)

    def test_rechaza_tipo_no_permitido(self):
        self.assertIn('comprobante', self.formulario(comprobante=archivo('xss.pdf', 'text/html')).errors)

    def test_rechaza_archivos_grandes(self):
        grande = archivo(contenido=b'0' * (5 * 1024 * 1024 + 1))
        self.assertIn('comprobante', self.formulario(comprobante=grande).errors)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ProcesarPagoTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        from django.conf import settings
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.consorcio, _ = crear_consorcio()
        usuario = User.objects.create_user('prop', password='clave')
        uf = UnidadFuncional.objects.create(
            propietario=Propietario.objects.create(usuario=usuario), consorcio=self.consorcio,
            piso=1, departamento='A', alicuota=Decimal('50'))
        liquidacion = Liquidacion.objects.create(consorcio=self.consorcio, periodo='2026-04', cerrada=True)
        detalle = DetalleLiquidacionUF.objects.create(
            liquidacion=liquidacion, unidad_funcional=uf, monto_total=Decimal('1000'))
        self.pago = Pago.objects.create(
            detalle_liquidacion=detalle, fecha_pago=date.today(),
            monto_pagado=Decimal('1000'), comprobante=archivo())
        self.client.force_login(User.objects.create_superuser('admin', 'admin@example.com', 'clave'))

    def procesar(self, accion):
        self.client.post(reverse('procesar_pago', args=[self.pago.pk]), {'accion': accion})
        self.pago.refresh_from_db()
        return self.pago.estado

    def test_validar_pendiente(self):
        self.assertEqual(self.procesar('validar'), 'validado')

    def test_no_se_puede_validar_un_rechazado(self):
        self.assertEqual(self.procesar('rechazar'), 'rechazado')
        self.assertEqual(self.procesar('validar'), 'rechazado')

    def test_no_se_puede_rechazar_un_validado(self):
        self.assertEqual(self.procesar('validar'), 'validado')
        self.assertEqual(self.procesar('rechazar'), 'validado')

    def test_accion_invalida_no_cambia_el_estado(self):
        self.assertEqual(self.procesar('cualquiera'), 'pendiente')

    def test_subir_comprobante_de_gasto_rechaza_html(self):
        gasto = Gasto.objects.create(
            consorcio=self.consorcio, concepto='Luz', monto=Decimal('10'), periodo='2026-04',
            fecha_comprobante=date.today(), liquidacion=self.pago.detalle_liquidacion.liquidacion)
        self.client.post(reverse('subir_comprobante', args=[gasto.pk]),
                         {'comprobante': archivo('xss.html', 'application/pdf', b'<script></script>')})
        gasto.refresh_from_db()
        self.assertFalse(gasto.comprobante)


class InicioPropietarioTests(TestCase):
    def setUp(self):
        self.consorcio, _ = crear_consorcio()
        self.usuario = User.objects.create_user('prop', password='clave')
        self.propietario = Propietario.objects.create(usuario=self.usuario)
        self.uf = UnidadFuncional.objects.create(
            propietario=self.propietario, consorcio=self.consorcio,
            piso=3, departamento='B', alicuota=Decimal('50'))
        self.client.force_login(self.usuario)

    def detalle(self, periodo, monto, vencimiento=None, uf=None):
        liquidacion = Liquidacion.objects.create(
            consorcio=self.consorcio, periodo=periodo, cerrada=True, fecha_vencimiento_1=vencimiento)
        return DetalleLiquidacionUF.objects.create(
            liquidacion=liquidacion, unidad_funcional=uf or self.uf, monto_total=Decimal(monto))

    def pago(self, detalle, monto, estado='pendiente'):
        return Pago.objects.create(detalle_liquidacion=detalle, fecha_pago=date.today(),
                                   monto_pagado=Decimal(monto), estado=estado, comprobante='x.pdf')

    def contexto(self, **parametros):
        return self.client.get(reverse('inicio_propietario'), parametros).context

    def test_suma_la_deuda_de_todos_los_periodos_impagos(self):
        self.detalle('2026-08', '10000', date(2026, 8, 15))
        septiembre = self.detalle('2026-09', '12000', date(2026, 9, 15))
        contexto = self.contexto()
        self.assertEqual(contexto['saldo'], Decimal('22000'))
        self.assertEqual(contexto['periodos_impagos'], 2)
        self.assertEqual(contexto['proximo_vencimiento'], date(2026, 8, 15))
        self.assertEqual(contexto["ultima"], septiembre)
        self.assertEqual(contexto['ultima_label'], 'Septiembre 2026')
        self.assertEqual([v['fecha'] for v in contexto['vencimientos']], [date(2026, 8, 15), date(2026, 9, 15)])

    def test_sin_deuda_esta_al_dia(self):
        self.pago(self.detalle('2026-09', '12000'), '12000', 'validado')
        contexto = self.contexto()
        self.assertEqual(contexto['saldo'], Decimal('0'))
        self.assertIsNone(contexto['a_pagar'])
        self.assertEqual(contexto['vencimientos'], [])
        self.assertContains(self.client.get(reverse('inicio_propietario')), 'Estás al día')

    def test_pago_en_revision_no_descuenta_del_saldo(self):
        detalle = self.detalle('2026-09', '12000')
        self.pago(detalle, '12000')
        contexto = self.contexto()
        self.assertEqual(contexto['saldo'], Decimal('12000'))
        self.assertEqual(contexto['pagos_en_revision'], 1)
        self.assertIsNone(contexto['a_pagar'])

    def test_informar_pago_apunta_al_periodo_impago_mas_viejo(self):
        viejo = self.detalle('2026-08', '10000')
        self.detalle('2026-09', '12000')
        self.assertEqual(self.contexto()['a_pagar'], viejo)

    def test_novedades_de_liquidaciones_y_pagos(self):
        detalle = self.detalle('2026-09', '12000')
        self.pago(detalle, '5000', 'rechazado')
        titulos = [n['titulo'] for n in self.contexto()['novedades']]
        self.assertIn('Nueva liquidación: Septiembre 2026', titulos)
        self.assertIn('Pago rechazado', titulos)

    def test_elige_la_unidad_por_parametro(self):
        otra = UnidadFuncional.objects.create(
            propietario=self.propietario, consorcio=self.consorcio,
            piso=1, departamento='A', alicuota=Decimal('50'))
        self.detalle('2026-09', '5000', uf=otra)
        self.assertEqual(self.contexto()['unidad'], otra)
        contexto = self.contexto(unidad=self.uf.pk)
        self.assertEqual(contexto['unidad'], self.uf)
        self.assertIsNone(contexto['ultima'])

    def test_mis_expensas_mantiene_la_uf_elegida_en_inicio(self):
        otro_consorcio, _ = crear_consorcio(nombre='Torre Dos', cuit='30712345679')
        otra = UnidadFuncional.objects.create(
            propietario=self.propietario, consorcio=otro_consorcio,
            piso=7, departamento='C', alicuota=Decimal('50'))
        self.client.get(reverse('inicio_propietario'), {'unidad': otra.pk})
        contexto = self.client.get(reverse('mis_expensas')).context
        self.assertEqual(contexto['consorcio'], otro_consorcio)
        self.assertEqual(contexto['unidad'], otra)
        self.client.get(reverse('mis_expensas'), {'consorcio': self.consorcio.pk})
        self.assertEqual(self.contexto()['unidad'], self.uf)

    def test_no_muestra_unidades_de_otro_propietario(self):
        otro = Propietario.objects.create(usuario=User.objects.create_user('otro', password='clave'))
        uf_ajena = UnidadFuncional.objects.create(
            propietario=otro, consorcio=self.consorcio, piso=2, departamento='C', alicuota=Decimal('10'))
        contexto = self.contexto(unidad=uf_ajena.pk)
        self.assertEqual(contexto['unidad'], self.uf)
        self.assertEqual(list(contexto['unidades']), [self.uf])

    def test_login_del_propietario_va_al_inicio(self):
        self.client.logout()
        respuesta = self.client.post(reverse('login'), {'username': 'prop', 'password': 'clave'})
        self.assertRedirects(respuesta, reverse('inicio_propietario'))


class InteresPorMoraTests(TestCase):
    def setUp(self):
        self.consorcio, _ = crear_consorcio()
        self.consorcio.tasa_interes_mensual = Decimal('3')
        self.consorcio.save()
        usuario = User.objects.create_user('prop', password='clave')
        self.uf = UnidadFuncional.objects.create(
            propietario=Propietario.objects.create(usuario=usuario), consorcio=self.consorcio,
            piso=3, departamento='B', alicuota=Decimal('50'))
        self.client.force_login(usuario)

    def detalle(self, monto='50', vencimiento=date(2026, 1, 10), periodo='2026-01'):
        liquidacion = Liquidacion.objects.create(
            consorcio=self.consorcio, periodo=periodo, cerrada=True, fecha_vencimiento_1=vencimiento)
        return DetalleLiquidacionUF.objects.create(
            liquidacion=liquidacion, unidad_funcional=self.uf, monto_total=Decimal(monto))

    def test_meses_de_atraso_cuenta_mes_o_fraccion(self):
        detalle = self.detalle()
        self.assertEqual(detalle.meses_de_atraso(date(2026, 1, 10)), 0)
        self.assertEqual(detalle.meses_de_atraso(date(2026, 1, 11)), 1)
        self.assertEqual(detalle.meses_de_atraso(date(2026, 2, 10)), 1)
        self.assertEqual(detalle.meses_de_atraso(date(2026, 2, 11)), 2)

    def test_ejemplo_del_mapping_50_al_3_por_ciento(self):
        self.assertEqual(self.detalle().interes(date(2026, 2, 5)), Decimal('1.50'))

    def test_interes_simple_por_varios_meses(self):
        self.assertEqual(self.detalle().interes(date(2026, 4, 5)), Decimal('4.50'))

    def test_sin_tasa_o_pagado_no_genera_interes(self):
        detalle = self.detalle()
        Pago.objects.create(detalle_liquidacion=detalle, fecha_pago=date.today(),
                            monto_pagado=Decimal('50'), estado='validado', comprobante='x.pdf')
        self.assertEqual(detalle.interes(date(2026, 3, 1)), Decimal('0'))
        self.consorcio.tasa_interes_mensual = 0
        self.consorcio.save()
        otro = self.detalle(periodo='2026-02')
        self.assertEqual(otro.interes(date(2026, 3, 1)), Decimal('0'))

    def test_inicio_separa_capital_e_intereses(self):
        detalle = self.detalle(monto='1000', vencimiento=date.today() - timedelta(days=1))
        contexto = self.client.get(reverse('inicio_propietario')).context
        self.assertEqual(contexto['capital'], Decimal('1000'))
        self.assertEqual(contexto['intereses'], Decimal('30.00'))
        self.assertEqual(contexto['saldo'], Decimal('1030.00'))
        self.assertEqual(detalle.interes(), Decimal('30.00'))


    def test_mis_expensas_suma_el_saldo_anterior_con_intereses(self):
        hoy = date.today()
        agosto = self.detalle(monto='1000', vencimiento=hoy - timedelta(days=40), periodo='2026-08')
        self.detalle(monto='500', vencimiento=hoy + timedelta(days=5), periodo='2026-09')
        contexto = self.client.get(reverse('mis_expensas'), {'periodo': '2026-09'}).context
        interes_agosto = agosto.interes()
        self.assertEqual([item['periodo'] for item in contexto['saldo_anterior']], ['Agosto 2026'])
        self.assertEqual(contexto['total_saldo_anterior'], Decimal('1000') + interes_agosto)
        self.assertEqual(contexto['interes'], Decimal('0'))
        self.assertEqual(contexto['total_a_pagar'], Decimal('1500') + interes_agosto)
        self.assertEqual(contexto['anterior'], '2026-08')

    def test_mis_expensas_no_arrastra_periodos_pagados(self):
        agosto = self.detalle(monto='1000', vencimiento=None, periodo='2026-08')
        Pago.objects.create(detalle_liquidacion=agosto, fecha_pago=date.today(),
                            monto_pagado=Decimal('1000'), estado='validado', comprobante='x.pdf')
        self.detalle(monto='500', vencimiento=None, periodo='2026-09')
        contexto = self.client.get(reverse('mis_expensas'), {'periodo': '2026-09'}).context
        self.assertEqual(contexto['saldo_anterior'], [])
        self.assertEqual(contexto['total_a_pagar'], Decimal('500'))


class ImputacionPagoTests(TestCase):
    """Story 5: el pago cancela primero el interés del mes más viejo, después su capital, y así."""

    def setUp(self):
        self.consorcio, _ = crear_consorcio()
        self.consorcio.tasa_interes_mensual = Decimal('3')
        self.consorcio.save()
        self.usuario = User.objects.create_user('prop', password='clave')
        self.uf = UnidadFuncional.objects.create(
            propietario=Propietario.objects.create(usuario=self.usuario), consorcio=self.consorcio,
            piso=3, departamento='B', alicuota=Decimal('50'))
        self.enero = self.detalle('2026-01', date(2026, 1, 10))
        self.febrero = self.detalle('2026-02', date(2026, 2, 10))

    def detalle(self, periodo, vencimiento, monto='50'):
        liquidacion = Liquidacion.objects.create(
            consorcio=self.consorcio, periodo=periodo, cerrada=True, fecha_vencimiento_1=vencimiento)
        return DetalleLiquidacionUF.objects.create(
            liquidacion=liquidacion, unidad_funcional=self.uf, monto_total=Decimal(monto))

    def pagar(self, monto, fecha, estado='validado'):
        return Pago.objects.create(detalle_liquidacion=self.febrero, fecha_pago=fecha,
                                   monto_pagado=Decimal(monto), estado=estado, comprobante='x.pdf')

    def refrescar(self):
        self.enero = DetalleLiquidacionUF.objects.get(pk=self.enero.pk)
        self.febrero = DetalleLiquidacionUF.objects.get(pk=self.febrero.pk)

    def test_ejemplo_del_mapping(self):
        pago = self.pagar('70', date(2026, 2, 5))
        self.assertEqual(
            [(i.detalle_liquidacion, i.concepto, i.monto) for i in pago.imputaciones.all()],
            [(self.enero, 'interes', Decimal('1.50')), (self.enero, 'capital', Decimal('50')),
             (self.febrero, 'capital', Decimal('18.50'))],
        )
        self.refrescar()
        self.assertTrue(self.enero.esta_pagado)
        self.assertEqual(self.febrero.deuda_total_actualizada, Decimal('31.50'))

    def test_el_resto_sigue_generando_interes(self):
        self.pagar('70', date(2026, 2, 5))
        self.refrescar()
        self.assertEqual(self.enero.interes(date(2026, 4, 1)), Decimal('0'))
        self.assertEqual(self.febrero.interes(date(2026, 3, 1)), Decimal('0.95'))  # 3% de 31,50

    def test_pago_parcial_reduce_el_interes_de_los_meses_siguientes(self):
        self.pagar('26.50', date(2026, 2, 5))  # 1,50 de interés + 25 de capital de enero
        self.refrescar()
        # Mes 1 sobre 50 (ya pagado) + mes 2 sobre 25 = 0,75 pendiente
        self.assertEqual(self.enero.interes(date(2026, 3, 1)), Decimal('0.75'))

    def test_lo_que_sobra_queda_como_saldo_a_favor(self):
        pago = self.pagar('200', date(2026, 2, 5))
        excedente = pago.imputaciones.get(concepto='excedente')
        self.assertEqual(excedente.monto, Decimal('200') - Decimal('101.50'))
        self.assertIsNone(excedente.detalle_liquidacion)

    def test_pago_pendiente_o_rechazado_no_se_imputa(self):
        self.pagar('70', date(2026, 2, 5), estado='pendiente')
        self.pagar('70', date(2026, 2, 5), estado='rechazado')
        self.assertFalse(ImputacionPago.objects.exists())

    def test_validar_desde_pagos_pendientes_imputa(self):
        pago = self.pagar('70', date(2026, 2, 5), estado='pendiente')
        self.client.force_login(User.objects.create_superuser('admin', 'admin@example.com', 'clave'))
        self.client.post(reverse('procesar_pago', args=[pago.pk]), {'accion': 'validar'})
        self.assertEqual(pago.imputaciones.count(), 3)

    def test_historial_muestra_la_imputacion(self):
        self.pagar('70', date(2026, 2, 5))
        self.client.force_login(self.usuario)
        respuesta = self.client.get(reverse('historial_pagos'))
        self.assertContains(respuesta, 'Interés 2026-01')
        self.assertContains(respuesta, 'Capital 2026-02')


    def test_recibo_de_pago_validado(self):
        pago = self.pagar('70', date(2026, 2, 5))
        self.client.force_login(self.usuario)
        respuesta = self.client.get(reverse('recibo_pago', args=[pago.pk]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.assertTrue(respuesta.content.startswith(b'%PDF'))
        self.assertContains(self.client.get(reverse('historial_pagos')), reverse('recibo_pago', args=[pago.pk]))

    def test_sin_recibo_si_no_esta_validado_o_es_de_otro(self):
        pendiente = self.pagar('70', date(2026, 2, 5), estado='pendiente')
        validado = self.pagar('10', date(2026, 2, 6))
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(reverse('recibo_pago', args=[pendiente.pk])).status_code, 404)
        otro = User.objects.create_user('otro', password='clave')
        Propietario.objects.create(usuario=otro)
        self.client.force_login(otro)
        self.assertEqual(self.client.get(reverse('recibo_pago', args=[validado.pk])).status_code, 404)

    def test_el_admin_tambien_descarga_el_recibo(self):
        pago = self.pagar('70', date(2026, 2, 5))
        self.client.force_login(User.objects.create_superuser('admin', 'admin@example.com', 'clave'))
        self.assertEqual(self.client.get(reverse('recibo_pago', args=[pago.pk])).status_code, 200)


class GastosDeMiUnidadTests(TestCase):
    """Story 4: los arreglos imputados a una UF se ven aparte en Mis Expensas."""

    def setUp(self):
        from consorcios.models import TipoReparto
        from .services import procesar_liquidacion_periodo
        self.consorcio, self.general = crear_consorcio()
        self.usuario = User.objects.create_user('prop', password='clave')
        self.uf = UnidadFuncional.objects.create(
            propietario=Propietario.objects.create(usuario=self.usuario), consorcio=self.consorcio,
            piso=3, departamento='B', alicuota=Decimal('50'))
        otro = Propietario.objects.create(usuario=User.objects.create_user('vecino', password='clave'))
        self.vecina = UnidadFuncional.objects.create(
            propietario=otro, consorcio=self.consorcio, piso=1, departamento='A', alicuota=Decimal('50'))
        particular = GrupoProrrateo.objects.create(
            consorcio=self.consorcio, rubro=self.general.rubro, nombre='Arreglos 3B', codigo='P',
            tipo_reparto=TipoReparto.PARTICULAR)
        particular.unidades.add(self.uf)
        liquidacion = Liquidacion.objects.create(consorcio=self.consorcio, periodo='2026-09', cerrada=True)
        for posicion, (concepto, grupo, monto) in enumerate([
            ('Limpieza', self.general, '1000'), ('Rotura de caño 3°B', particular, '30000'),
        ]):
            Gasto.objects.create(liquidacion=liquidacion, consorcio=self.consorcio, periodo='2026-09',
                                 fecha_comprobante=date(2026, 9, 30), posicion=posicion, concepto=concepto,
                                 tipo='ordinario', grupo=grupo, monto=Decimal(monto))
        procesar_liquidacion_periodo(liquidacion)

    def contexto(self, usuario):
        self.client.force_login(usuario)
        return self.client.get(reverse('mis_expensas'), {'periodo': '2026-09'}).context

    def test_mi_uf_ve_el_arreglo_aparte_y_lo_paga_completo(self):
        particulares = self.contexto(self.usuario)['gastos_particulares']
        self.assertEqual([item['gasto'].concepto for item in particulares], ['Rotura de caño 3°B'])
        self.assertEqual(particulares[0]['monto_asignado'], Decimal('30000'))
        self.assertEqual(particulares[0]['compartido_con'], 0)

    def test_la_vecina_no_lo_ve_ni_lo_paga(self):
        self.assertEqual(self.contexto(self.vecina.propietario.usuario)['gastos_particulares'], [])


    def test_el_admin_decide_si_el_propietario_ve_la_factura(self):
        gasto = Gasto.objects.get(concepto='Rotura de caño 3°B')
        gasto.comprobante = 'comprobantes/factura.pdf'
        gasto.save()
        self.client.force_login(self.usuario)
        url = reverse('mis_expensas')
        self.assertContains(self.client.get(url, {'periodo': '2026-09'}), 'Ver factura')
        self.client.force_login(User.objects.create_superuser('admin', 'admin@example.com', 'clave'))
        self.client.post(reverse('visibilidad_comprobante', args=[gasto.pk]))
        gasto.refresh_from_db()
        self.assertFalse(gasto.comprobante_visible)
        self.client.force_login(self.usuario)
        self.assertNotContains(self.client.get(url, {'periodo': '2026-09'}), 'Ver factura')
