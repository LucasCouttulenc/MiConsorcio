from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from xml.sax.saxutils import escape

from django.db import transaction

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import simpleSplit
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.units import mm

from consorcios.models import UnidadFuncional, TipoReparto

from .models import DetalleLiquidacionUF, TipoGasto


def dinero(valor):
    return Decimal(valor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)



def formatear_moneda(valor):
    """1234.5 -> '$ 1.234,50' (formato es-AR)."""
    valor = Decimal(valor or 0)
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"$ {texto}"


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

    for gasto in liquidacion.gastos_cargados.select_related('grupo').prefetch_related('grupo__unidades'):
        monto = gasto.monto
        es_ordinario = gasto.tipo == TipoGasto.ORDINARIO
        if es_ordinario:
            total_ordinario += monto
        else:
            total_extraordinario += monto

        columna = gasto.grupo
        tipo_rep = columna.tipo_reparto if columna else TipoReparto.GENERAL
        seleccion = {uf.pk for uf in columna.unidades.all()} if columna else set()
        if tipo_rep == TipoReparto.PARTICULAR:
            pagadores = [uf for uf in ufs if uf.pk in seleccion]
        elif tipo_rep == TipoReparto.PARCIAL:
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
    gastos = [['Concepto', 'Tipo', 'Rubro', 'Columna', 'Monto']]
    for gasto in liquidacion.gastos_cargados.select_related('grupo', 'grupo__rubro').order_by('posicion'):
        concepto = simpleSplit(gasto.concepto, 'Helvetica', 9, 190)
        rubro_nombre = gasto.grupo.rubro.nombre if gasto.grupo and gasto.grupo.rubro else '-'
        gastos.append([Paragraph('<br/>'.join(escape(linea) for linea in concepto), estilos['Normal']),
                       gasto.get_tipo_display(),
                       Paragraph(escape(rubro_nombre), estilos['Normal']),
                       Paragraph(escape(gasto.grupo.nombre if gasto.grupo else '-'), estilos['Normal']),
                       f'$ {gasto.monto:.2f}'])
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





def generar_resumen_uf_pdf(detalle):
    """
    Genera el PDF de resumen de liquidación para UNA unidad funcional.
    Devuelve los bytes del PDF.
    """
    liquidacion = detalle.liquidacion
    uf = detalle.unidad_funcional
    consorcio = liquidacion.consorcio
    admin = (liquidacion.datos_borrador or {}).get('administracion', {})
    propietario = (
        uf.propietario.usuario.get_full_name()
        or uf.propietario.usuario.username
    )

    detalle_gastos = calcular_detalle_uf(detalle)

    # ---- Estilos ----
    base = getSampleStyleSheet()["Normal"]
    est = {
        'titulo': ParagraphStyle('t', parent=base, fontName='Helvetica-Bold', fontSize=16,
                                 leading=20, textColor=colors.HexColor('#1c3e7c')),
        'subt': ParagraphStyle('s', parent=base, fontName='Helvetica', fontSize=9,
                               leading=12, textColor=colors.HexColor('#555555')),
        'th': ParagraphStyle('th', parent=base, fontName='Helvetica-Bold', fontSize=9,
                             leading=11, textColor=colors.white, alignment=TA_CENTER),
        'th_left': ParagraphStyle('thl', parent=base, fontName='Helvetica-Bold', fontSize=9,
                                  leading=11, textColor=colors.white),
        'rubro': ParagraphStyle('r', parent=base, fontName='Helvetica-Bold', fontSize=9,
                                leading=12),
        'normal': ParagraphStyle('n', parent=base, fontName='Helvetica', fontSize=9, leading=11),
        'num': ParagraphStyle('num', parent=base, fontName='Helvetica', fontSize=9,
                              leading=11, alignment=TA_RIGHT),
        'num_b': ParagraphStyle('numb', parent=base, fontName='Helvetica-Bold', fontSize=9,
                                leading=11, alignment=TA_RIGHT),
        'bold': ParagraphStyle('b', parent=base, fontName='Helvetica-Bold', fontSize=9,
                               leading=11),
        'center': ParagraphStyle('c', parent=base, fontName='Helvetica', fontSize=9,
                                 leading=11, alignment=TA_CENTER),
        'center_b': ParagraphStyle('cb', parent=base, fontName='Helvetica-Bold', fontSize=9,
                                   leading=11, alignment=TA_CENTER),
    }

    ANCHO = A4[0] - 30 * mm
    story = []

    # ---- Banner ----
    banner = Table(
        [[Paragraph('RESUMEN DE LIQUIDACIÓN', ParagraphStyle(
            'bt', parent=base, fontName='Helvetica-Bold', fontSize=14, leading=18,
            alignment=TA_CENTER, textColor=colors.white))]],
        colWidths=[ANCHO],
    )
    banner.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#1c3e7c')),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(banner)
    story.append(Spacer(1, 5 * mm))

    # ---- Datos generales ----
    periodo_str = liquidacion.periodo
    story.append(Paragraph(
        f"<b>Consorcio:</b> {escape(consorcio.nombre)}  ·  "
        f"<b>Período:</b> {escape(periodo_str)}  ·  "
        f"<b>Cierre:</b> {_fecha_simple(liquidacion.fecha_cierre)}  ·  "
        f"<b>1° Venc.:</b> {_fecha_simple(liquidacion.fecha_vencimiento_1)}",
        est['subt'],
    ))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        f"<b>Unidad:</b> {uf.piso}° {uf.departamento or ''}  ·  "
        f"<b>Propietario:</b> {escape(propietario)}  ·  "
        f"<b>Alícuota:</b> {round(detalle.alicuota):.0f}%",
        est['subt'],
    ))
    story.append(Spacer(1, 6 * mm))

    # ---- Tabla de resumen (cada gasto individual) ----
    filas = [[
        Paragraph('Concepto', est['th_left']),
        Paragraph('Reparto', est['th']),
        Paragraph('Tipo', est['th']),
        Paragraph('Monto', est['th']),
    ]]

    total_ord = Decimal('0.00')
    total_ext = Decimal('0.00')

    if not detalle_gastos:
        filas.append([
            Paragraph('Sin gastos en esta liquidación.', est['center']),
            '', '', '',
        ])
    else:
        for item in detalle_gastos:
            es_ord = item['tipo_gasto'] == 'Ordinario'
            if es_ord:
                total_ord += item['monto']
            else:
                total_ext += item['monto']

            filas.append([
                Paragraph(escape(item['concepto']), est['normal']),
                Paragraph(escape(item['tipo_reparto']), est['center']),
                Paragraph(escape(item['tipo_gasto']), est['center']),
                Paragraph(formatear_moneda(item['monto']), est['center']),
            ])

        # Fila TOTAL
        filas.append([
            Paragraph('TOTAL', est['center']),
            '',
            '',
            Paragraph(formatear_moneda(total_ord + total_ext), est['center']),
        ])

    tabla = Table(
        filas,
        colWidths=[ANCHO * 0.48, ANCHO * 0.16, ANCHO * 0.16, ANCHO * 0.20],
        repeatRows=1,
    )
    ultima = len(filas) - 1
    estilos_tabla = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1c3e7c')),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#bdbdbd')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]
    if detalle_gastos:
        estilos_tabla.append(('BACKGROUND', (0, ultima), (-1, ultima),
                              colors.HexColor('#e9ecef')))
    tabla.setStyle(TableStyle(estilos_tabla))
    story.append(tabla)

    # ---- Total general ----
    if detalle_gastos:
        story.append(Spacer(1, 4 * mm))
        total_gen = total_ord + total_ext
        story.append(Paragraph(
            f"<b>Total a pagar por esta unidad:</b> {formatear_moneda(total_gen)}",
            ParagraphStyle('tg', parent=base, fontName='Helvetica-Bold', fontSize=11,
                           leading=14, alignment=TA_RIGHT,
                           textColor=colors.HexColor('#1c3e7c')),
        ))

    # ---- Datos de administración (al pie) ----
    if admin.get('admin_razon') or admin.get('admin_nombre'):
        story.append(Spacer(1, 8 * mm))
        story.append(Paragraph(
            f"<b>Administración:</b> {escape(admin.get('admin_razon') or '-')} · "
            f"{escape(admin.get('admin_nombre') or '-')}",
            est['subt'],
        ))
        if admin.get('admin_mail') or admin.get('admin_telefono'):
            story.append(Paragraph(
                f"<b>Contacto:</b> {escape(admin.get('admin_mail') or '-')} · "
                f"{escape(admin.get('admin_telefono') or '-')}",
                est['subt'],
            ))

    # ---- Build ----
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=15 * mm,
        title=f"Resumen UF {uf.pk} - {periodo_str}",
    )
    doc.build(story)
    return buffer.getvalue()

def _fecha_simple(f):
    if not f:
        return '--/--/----'
    if isinstance(f, str):
        partes = f.split('-')
        return f"{partes[2]}/{partes[1]}/{partes[0]}" if len(partes) == 3 else f
    return f.strftime('%d/%m/%Y')




def calcular_detalle_uf(detalle):
    """
    Devuelve una lista plana de todos los gastos de la liquidación, con:
      - concepto
      - tipo_reparto (display: General / Parcial / Particular)
      - tipo_gasto (display: Ordinario / Extraordinario)
      - monto: parte que le corresponde a esta UF (Decimal 0.00 si no participa)
    """
    liquidacion = detalle.liquidacion
    uf = detalle.unidad_funcional
    consorcio = liquidacion.consorcio
    ufs = list(UnidadFuncional.objects.filter(consorcio=consorcio))

    filas = []
    gastos = liquidacion.gastos_cargados.select_related(
        'grupo'
    ).prefetch_related('grupo__unidades').order_by('posicion')

    for gasto in gastos:
        columna = gasto.grupo
        if not columna:
            continue

        seleccion = {u.pk for u in columna.unidades.all()}
        if columna.tipo_reparto == TipoReparto.PARTICULAR:
            pagadores = [u for u in ufs if u.pk in seleccion]
        elif columna.tipo_reparto == TipoReparto.PARCIAL:
            pagadores = [u for u in ufs if u.pk not in seleccion]
        else:
            pagadores = list(ufs)

        if not pagadores:
            pagadores = list(ufs)

        # Monto asignado a esta UF (0.00 si no participa)
        monto_uf = Decimal('0.00')
        if pagadores and uf.pk in {u.pk for u in pagadores}:
            pesos = [u.alicuota for u in pagadores]
            suma = sum(pesos)
            if suma <= 0:
                pesos = [Decimal('1')] * len(pagadores)
                suma = Decimal(len(pagadores))

            asignado = Decimal('0.00')
            ultimo = len(pagadores) - 1
            for i, u in enumerate(pagadores):
                if i < ultimo:
                    parte = dinero(gasto.monto * pesos[i] / suma)
                    asignado += parte
                else:
                    parte = gasto.monto - asignado
                if u.pk == uf.pk:
                    monto_uf = parte
                    break

        filas.append({
            'concepto': gasto.concepto,
            'tipo_reparto': columna.get_tipo_reparto_display(),
            'tipo_gasto': gasto.get_tipo_display(),
            'monto': monto_uf,
        })

    return filas
