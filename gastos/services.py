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

from consorcios.models import CoeficienteUF, UnidadFuncional
from .models import DetalleLiquidacionUF, TipoGasto


def dinero(valor):
    return Decimal(valor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


@transaction.atomic
def procesar_liquidacion_periodo(liquidacion):
    # Totales por grupo y tipo, a partir de los gastos cargados en esta liquidación
    totales = defaultdict(lambda: {TipoGasto.ORDINARIO: Decimal('0'), TipoGasto.EXTRAORDINARIO: Decimal('0')})
    for gasto in liquidacion.gastos_cargados.all():
        totales[gasto.grupo_id][gasto.tipo] += gasto.monto

    liquidacion.total_ordinario = dinero(sum((m[TipoGasto.ORDINARIO] for m in totales.values()), Decimal('0')))
    liquidacion.total_extraordinario = dinero(sum((m[TipoGasto.EXTRAORDINARIO] for m in totales.values()), Decimal('0')))
    liquidacion.save(update_fields=['total_ordinario', 'total_extraordinario'])

    liquidacion.detalles_uf.all().delete()

    coeficientes = defaultdict(dict)
    for coef in CoeficienteUF.objects.filter(unidad_funcional__consorcio=liquidacion.consorcio):
        coeficientes[coef.unidad_funcional_id][coef.grupo_id] = coef.porcentaje

    detalles = []
    for uf in UnidadFuncional.objects.filter(consorcio=liquidacion.consorcio):
        ordinario = extraordinario = Decimal('0')
        for grupo_id, montos in totales.items():
            factor = coeficientes[uf.pk].get(grupo_id, Decimal('0')) / Decimal('100')
            ordinario += montos[TipoGasto.ORDINARIO] * factor
            extraordinario += montos[TipoGasto.EXTRAORDINARIO] * factor
        ordinario, extraordinario = dinero(ordinario), dinero(extraordinario)
        detalles.append(DetalleLiquidacionUF(
            liquidacion=liquidacion, unidad_funcional=uf,
            monto_ordinario=ordinario, monto_extraordinario=extraordinario,
            monto_total=ordinario + extraordinario))
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
