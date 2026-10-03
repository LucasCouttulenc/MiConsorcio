from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from xml.sax.saxutils import escape

from django.db import transaction
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import simpleSplit
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from consorcios.models import UnidadFuncional

from .models import DetalleLiquidacionUF, TipoGasto, ModoReparto


def dinero(valor):
    return Decimal(valor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


@transaction.atomic
def procesar_liquidacion_periodo(liquidacion):
    """
    Calcula los totales ordinario/extraordinario del período y arma el
    DetalleLiquidacionUF repartiendo CADA gasto solo entre las UF que lo pagan
    (según su modo de reparto), proporcional a la alícuota de cada una.
    """
    ufs = list(UnidadFuncional.objects.filter(consorcio=liquidacion.consorcio))
    acum = {uf.pk: {'ord': Decimal('0.00'), 'ext': Decimal('0.00')} for uf in ufs}
    total_ordinario = Decimal('0')
    total_extraordinario = Decimal('0')

    for gasto in liquidacion.gastos_cargados.prefetch_related('unidades'):
        monto = gasto.monto
        es_ordinario = gasto.tipo == TipoGasto.ORDINARIO
        if es_ordinario:
            total_ordinario += monto
        else:
            total_extraordinario += monto

        seleccion = {uf.pk for uf in gasto.unidades.all()}
        if gasto.modo_reparto == ModoReparto.PARTICULAR:
            pagadores = [uf for uf in ufs if uf.pk in seleccion]
        elif gasto.modo_reparto == ModoReparto.PARCIAL:
            pagadores = [uf for uf in ufs if uf.pk not in seleccion]
        else:
            pagadores = list(ufs)
        if not pagadores:
            # salvaguarda: si no quedaría nadie pagando, lo pagan todas
            pagadores = list(ufs)
        if not pagadores:
            continue

        pesos = [uf.alicuota for uf in pagadores]
        suma = sum(pesos)
        if suma <= 0:
            # sin alícuotas válidas entre los pagadores: partes iguales
            pesos = [Decimal('1')] * len(pagadores)
            suma = Decimal(len(pagadores))

        asignado = Decimal('0.00')
        ultimo = len(pagadores) - 1
        for i, uf in enumerate(pagadores):
            if i < ultimo:
                parte = dinero(monto * pesos[i] / suma)
                asignado += parte
            else:
                parte = monto - asignado  # el último absorbe el redondeo
            if es_ordinario:
                acum[uf.pk]['ord'] += parte
            else:
                acum[uf.pk]['ext'] += parte

    liquidacion.total_ordinario = dinero(total_ordinario)
    liquidacion.total_extraordinario = dinero(total_extraordinario)
    liquidacion.save(update_fields=['total_ordinario', 'total_extraordinario'])

    liquidacion.detalles_uf.all().delete()
    detalles = [
        DetalleLiquidacionUF(
            liquidacion=liquidacion,
            unidad_funcional=uf,
            alicuota=uf.alicuota,
            monto_ordinario=acum[uf.pk]['ord'],
            monto_extraordinario=acum[uf.pk]['ext'],
            monto_total=acum[uf.pk]['ord'] + acum[uf.pk]['ext'],
        )
        for uf in ufs
    ]
    DetalleLiquidacionUF.objects.bulk_create(detalles)
    return liquidacion


def generar_pdf_liquidacion(liquidacion):
    """Genera el documento final con los datos persistidos."""
    salida = BytesIO()
    documento = SimpleDocTemplate(salida, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    estilos = getSampleStyleSheet()
    historia = [Paragraph('Liquidación de expensas', estilos['Title'])]
    admin = liquidacion.datos_borrador.get('administracion', {})
    for etiqueta, valor in (
        ('Consorcio', liquidacion.consorcio.nombre), ('CUIT', liquidacion.consorcio.cuit),
        ('Período', liquidacion.periodo), ('Cierre', liquidacion.fecha_cierre),
        ('Emisión', liquidacion.fecha_emision),
        ('Vencimiento', liquidacion.fecha_vencimiento_1),
        ('Administración', admin.get('admin_razon', '')),
        ('Administrador', admin.get('admin_nombre', '')),
        ('Domicilio', admin.get('admin_domicilio', '')),
        ('Situación fiscal', admin.get('admin_fiscal', '')),
        ('CUIT administración', admin.get('admin_cuit', '')),
        ('RPA', admin.get('admin_rpa', '')),
        ('Teléfono', admin.get('admin_telefono', '')),
        ('Correo', admin.get('admin_mail', '')),
    ):
        historia.append(Paragraph(escape(f'{etiqueta}: {valor or "-"}'), estilos['Normal']))
    historia.extend([Spacer(1, 16), Paragraph('Gastos', estilos['Heading2'])])
    gastos = [['Concepto', 'Tipo', 'Rubro', 'Grupo', 'Monto']]
    for gasto in liquidacion.gastos_cargados.select_related('grupo').order_by('posicion'):
        concepto = simpleSplit(gasto.concepto, 'Helvetica', 9, 190)
        gastos.append([Paragraph('<br/>'.join(escape(linea) for linea in concepto), estilos['Normal']),
                       gasto.get_tipo_display(), Paragraph(escape(gasto.subtipo or '-'), estilos['Normal']),
                       Paragraph(escape(gasto.grupo.nombre), estilos['Normal']), f'$ {gasto.monto:.2f}'])
    tabla = Table(gastos, colWidths=[165, 75, 95, 95, 65], repeatRows=1)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1c3e7c')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), .4, colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    historia.extend([tabla, Spacer(1, 12)])
    historia.append(Paragraph(f'Total ordinario: $ {liquidacion.total_ordinario:.2f}', estilos['Normal']))
    historia.append(Paragraph(f'Total extraordinario: $ {liquidacion.total_extraordinario:.2f}', estilos['Normal']))
    historia.append(Paragraph(f'Total: $ {(liquidacion.total_ordinario + liquidacion.total_extraordinario):.2f}', estilos['Heading2']))
    historia.extend([Spacer(1, 12), Paragraph('Detalle por unidad funcional', estilos['Heading2'])])
    unidades = [['Unidad', 'Propietario', 'Ordinario', 'Extraordinario', 'Total']]
    for detalle in liquidacion.detalles_uf.select_related('unidad_funcional__propietario__usuario').all():
        uf = detalle.unidad_funcional
        unidades.append([f'{uf.piso}° {uf.departamento or ""}',
                         Paragraph(escape(uf.propietario.usuario.get_full_name() or uf.propietario.usuario.username), estilos['Normal']),
                         f'$ {detalle.monto_ordinario:.2f}',
                         f'$ {detalle.monto_extraordinario:.2f}', f'$ {detalle.monto_total:.2f}'])
    tabla_uf = Table(unidades, colWidths=[75, 145, 90, 95, 90], repeatRows=1)
    tabla_uf.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), .4, colors.lightgrey),
                                 ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8eff9'))]))
    historia.append(tabla_uf)
    documento.build(historia)
    return salida.getvalue()
