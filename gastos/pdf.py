# gastos/pdf.py
"""
Genera el PDF de una liquidación replicando la vista previa del formulario:
banner, datos de administración / consorcio, una tabla por subtipo con una
columna por grupo, subtotales y total estimado general.
"""
from collections import OrderedDict
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

MESES = {
    "01": "Enero", "02": "Febrero", "03": "Marzo", "04": "Abril",
    "05": "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto",
    "09": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre",
}

AZUL = colors.HexColor("#1b365d")
GRIS_HEADER = colors.HexColor("#e2e3e5")
GRIS_SUBTOTAL = colors.HexColor("#f1f3f5")
GRIS_TOTAL = colors.HexColor("#e9ecef")
BORDE = colors.HexColor("#bdbdbd")

ANCHO_UTIL = A4[0] - 30 * mm  # márgenes de 15 mm


def _money(valor):
    """1234.5 -> '$ 1.234,50' (formato es-AR)."""
    valor = Decimal(valor or 0)
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"$ {texto}"


def _fecha(fecha):
    if not fecha:
        return "--/--/----"
    if isinstance(fecha, str):
        partes = fecha.split("-")
        return f"{partes[2]}/{partes[1]}/{partes[0]}" if len(partes) == 3 else fecha
    return fecha.strftime("%d/%m/%Y")


def _txt(valor, defecto="-"):
    valor = "" if valor is None else str(valor).strip()
    return escape(valor) if valor else defecto


def _estilos():
    base = getSampleStyleSheet()["Normal"]
    return {
        "normal": ParagraphStyle("n", parent=base, fontName="Helvetica", fontSize=8.5, leading=11),
        "small": ParagraphStyle("s", parent=base, fontName="Helvetica", fontSize=8, leading=10),
        "bold": ParagraphStyle("b", parent=base, fontName="Helvetica-Bold", fontSize=8.5, leading=11),
        "th": ParagraphStyle("th", parent=base, fontName="Helvetica-Bold", fontSize=8, leading=10, alignment=TA_CENTER),
        "th_left": ParagraphStyle("thl", parent=base, fontName="Helvetica-Bold", fontSize=8, leading=10),
        "subtipo": ParagraphStyle("st", parent=base, fontName="Helvetica-Bold", fontSize=9, leading=11,
                                  alignment=TA_CENTER, textColor=colors.white),
        "num": ParagraphStyle("num", parent=base, fontName="Helvetica", fontSize=8.5, leading=11, alignment=TA_RIGHT),
        "num_b": ParagraphStyle("numb", parent=base, fontName="Helvetica-Bold", fontSize=8.5, leading=11,
                                alignment=TA_RIGHT),
        "banner_t": ParagraphStyle("bt", parent=base, fontName="Helvetica-Bold", fontSize=15, leading=18,
                                   alignment=TA_CENTER, textColor=colors.white),
        "banner_p": ParagraphStyle("bp", parent=base, fontName="Helvetica", fontSize=9, leading=12,
                                   alignment=TA_CENTER, textColor=colors.white),
        "h6": ParagraphStyle("h6", parent=base, fontName="Helvetica-Bold", fontSize=9.5, leading=12,
                             textColor=AZUL),
        "titulo": ParagraphStyle("tit", parent=base, fontName="Helvetica-Bold", fontSize=10, leading=13),
    }


def _anchos(cantidad_grupos, ancho_total=ANCHO_UTIL):
    """Concepto pesa 2, cada columna de grupo pesa 1 (igual que el preview)."""
    columnas = max(1, cantidad_grupos)
    unidad = ancho_total / (2 + columnas)
    return [unidad * 2] + [unidad] * columnas


def _banner(liquidacion, est):
    mes = liquidacion.periodo.split("-")[1] if "-" in liquidacion.periodo else ""
    anio = liquidacion.periodo.split("-")[0]
    periodo = f"{MESES.get(mes, mes)} {anio}"

    filas = [
        [Paragraph("EXPENSAS MICONSORCIO", est["banner_t"])],
        [Paragraph(f"Liquidación: {periodo}", est["banner_p"])],
        [Paragraph(f"Cierre de expensas al: {_fecha(liquidacion.fecha_cierre)}", est["banner_p"])],
        [Paragraph(f"Vencimiento: {_fecha(liquidacion.fecha_vencimiento_1)}", est["banner_p"])],
    ]
    tabla = Table(filas, colWidths=[ANCHO_UTIL])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AZUL),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
    ]))
    return tabla


def _cabecera(liquidacion, admin, est):
    consorcio = liquidacion.consorcio
    admin = admin or {}

    izquierda = [
        Paragraph(_txt(admin.get("admin_razon")), est["h6"]),
        Paragraph(f"<b>Nombre:</b> {_txt(admin.get('admin_nombre'))}", est["small"]),
        Paragraph(f"<b>Domicilio:</b> {_txt(admin.get('admin_domicilio'))}", est["small"]),
        Paragraph(f"<b>Situación Fiscal:</b> {_txt(admin.get('admin_fiscal'))}", est["small"]),
        Paragraph(f"<b>CUIT:</b> {_txt(admin.get('admin_cuit'))}", est["small"]),
        Paragraph(f"<b>RPA:</b> {_txt(admin.get('admin_rpa'))}", est["small"]),
        Paragraph(f"<b>Te.:</b> {_txt(admin.get('admin_telefono'))}", est["small"]),
        Paragraph(f"<b>Mail:</b> {_txt(admin.get('admin_mail'))}", est["small"]),
    ]

    direccion = f"{getattr(consorcio, 'calle', '')} {getattr(consorcio, 'altura', '')}".strip()
    cp = getattr(consorcio, "codigo_postal", "")
    if cp:
        direccion = f"{direccion}, CP {cp}"

    derecha = [
        Paragraph("CONSORCIO", est["h6"]),
        Paragraph(f"<b>Nombre:</b> {_txt(consorcio.nombre)}", est["small"]),
        Paragraph(f"<b>Dirección:</b> {_txt(direccion)}", est["small"]),
        Paragraph(f"<b>CUIT:</b> {_txt(getattr(consorcio, 'cuit', ''))}", est["small"]),
        Paragraph(f"<b>SUTERH:</b> {_txt(getattr(consorcio, 'clave_suterh', ''))}", est["small"]),
    ]

    mitad = ANCHO_UTIL / 2
    tabla = Table([[izquierda, derecha]], colWidths=[mitad, mitad])
    tabla.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDE),
        ("LINEAFTER", (0, 0), (0, 0), 0.5, BORDE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return tabla


def _tabla_subtipo(nombre_subtipo, gastos, est):
    """Una tabla por subtipo. Agrupa columnas que tengan mismo código y tipo de reparto."""
    
    columnas_agrupadas = OrderedDict()
    for g in gastos:
        if g.grupo:
            clave = (g.grupo.tipo_reparto, g.grupo.codigo)
            label_tabla = g.grupo.codigo
            label_total = f"{g.grupo.codigo} ({g.grupo.get_tipo_reparto_display()})"
        else:
            clave = ('general', 'Sin grupo')
            label_tabla = 'Sin grupo'
            label_total = 'Sin grupo'
            
        if clave not in columnas_agrupadas:
            columnas_agrupadas[clave] = {'label_tabla': label_tabla, 'label_total': label_total, 'gastos': []}
        columnas_agrupadas[clave]['gastos'].append(g)
        
    claves_usadas = list(columnas_agrupadas.keys())
    columnas = len(claves_usadas)
    anchos = _anchos(columnas)

    # En el encabezado de la tabla usamos el nombre limpio (A, B, C)
    encabezado_grupos = [Paragraph(escape(columnas_agrupadas[c]['label_tabla']), est["th"]) for c in claves_usadas]
    filas = [
        [Paragraph(escape(nombre_subtipo), est["subtipo"])] + [""] * columnas,
        [Paragraph("Concepto / Detalle", est["th_left"])] + encabezado_grupos,
    ]

    subtotales = {clave: Decimal("0.00") for clave in claves_usadas}
    for gasto in gastos:
        if gasto.grupo:
            clave_gasto = (gasto.grupo.tipo_reparto, gasto.grupo.codigo)
        else:
            clave_gasto = ('general', 'Sin grupo')

        fila = [Paragraph(escape(gasto.concepto or "(Sin concepto)"), est["normal"])]
        for clave in claves_usadas:
            if clave_gasto == clave:
                subtotales[clave] += gasto.monto
                fila.append(Paragraph(_money(gasto.monto), est["num_b"]))
            else:
                fila.append(Paragraph("-", est["th"]))
        filas.append(fila)

    filas.append(
        [Paragraph(f"SUBTOTAL {escape(nombre_subtipo)}:", est["bold"])]
        + [Paragraph(_money(subtotales[clave]), est["num_b"]) for clave in claves_usadas]
    )

    tabla = Table(filas, colWidths=anchos, repeatRows=2)
    ultima = len(filas) - 1
    tabla.setStyle(TableStyle([
        ("SPAN", (0, 0), (-1, 0)),
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("BACKGROUND", (0, 1), (-1, 1), GRIS_HEADER),
        ("BACKGROUND", (0, ultima), (-1, ultima), GRIS_SUBTOTAL),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    
    labels_total = {c: columnas_agrupadas[c]['label_total'] for c in claves_usadas}
    return tabla, subtotales, labels_total


def _tabla_total_general(totales, etiquetas, est):
    claves = list(totales.keys())
    anchos = _anchos(len(claves))
    fila = [Paragraph("TOTAL ESTIMADO GENERAL:", est["bold"])] + [
        Paragraph(_money(totales[clave]), est["num_b"]) for clave in claves
    ]
    # En el Total General sí usamos la etiqueta con el tipo de reparto
    encabezado = [Paragraph("", est["th_left"])] + [
        Paragraph(escape(etiquetas[clave]), est["th"]) for clave in claves
    ]
    tabla = Table([encabezado, fila], colWidths=anchos)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GRIS_HEADER),
        ("BACKGROUND", (0, 1), (-1, 1), GRIS_TOTAL),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDE),
        ("BOX", (0, 0), (-1, -1), 1.2, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tabla


def generar_pdf_liquidacion(liquidacion, gastos=None, admin=None):
    if gastos is None:
        gastos = liquidacion.gastos_cargados.select_related('grupo').order_by('posicion')
    if admin is None:
        admin = (liquidacion.datos_borrador or {}).get('administracion', {})
    est = _estilos()
    gastos = list(gastos)

    por_subtipo = OrderedDict()
    for g in gastos:
        clave = (g.grupo.rubro.nombre if g.grupo and g.grupo.rubro else "GASTOS GENERALES").strip().upper()
        por_subtipo.setdefault(clave, []).append(g)

    story = [
        _banner(liquidacion, est),
        Spacer(1, 4 * mm),
        _cabecera(liquidacion, admin, est),
        Spacer(1, 6 * mm),
        Paragraph("Resumen de Gastos Cargados", est["titulo"]),
        Spacer(1, 2 * mm),
    ]

    totales = {}
    etiquetas = {}
    if not por_subtipo:
        story.append(Paragraph("Sin gastos ingresados.", est["normal"]))
    else:
        for nombre, lista in por_subtipo.items():
            tabla, subtotales, labels = _tabla_subtipo(nombre, lista, est)
            story.append(tabla)
            story.append(Spacer(1, 4 * mm))
            for clave, valor in subtotales.items():
                totales[clave] = totales.get(clave, Decimal("0.00")) + valor
                etiquetas[clave] = labels[clave]
        story.append(_tabla_total_general(totales, etiquetas, est))
        
    # ---RESUMEN DE CAJA ---    
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("Resumen de Caja del Período", est["titulo"]))
    story.append(Spacer(1, 2 * mm))
    story.append(_tabla_resumen_caja(liquidacion, est))
        
    # --- Detalle por UF ---
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("Estado de Cuentas y Prorrateo", est["titulo"]))
    story.append(Spacer(1, 2 * mm))
    story.append(_tabla_detalle_uf(liquidacion, est))

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=15 * mm,
        title=f"Liquidación {liquidacion.periodo} - {liquidacion.consorcio.nombre}",
    )
    doc.build(story)
    return buffer.getvalue()

def _tabla_detalle_uf(liquidacion, est):
    encabezado = [
        Paragraph("U.F.", est["subtipo"]),
        Paragraph("Dpto", est["subtipo"]),
        Paragraph("Propietario", est["subtipo"]),
        Paragraph("%UF", est["subtipo"]),
        Paragraph("Ordinario", est["subtipo"]),
        Paragraph("Extraord.", est["subtipo"]),
        Paragraph("Total", est["subtipo"]),
    ]
    con_fondo = bool(liquidacion.total_fondo_reserva)
    if con_fondo:
        encabezado.insert(6, Paragraph("F. reserva", est["subtipo"]))

    filas = [encabezado]
    total_ord = Decimal("0.00")
    total_ext = Decimal("0.00")
    total_gen = Decimal("0.00")

    detalles = liquidacion.detalles_uf.select_related(
        'unidad_funcional__propietario__usuario'
    ).order_by('unidad_funcional__piso', 'unidad_funcional__departamento')

    for detalle in detalles:
        uf = detalle.unidad_funcional
        propietario = (
            uf.propietario.usuario.get_full_name()
            or uf.propietario.usuario.username
        )
        filas.append([
            Paragraph(str(uf.pk).zfill(3), est["th"]),
            Paragraph(f"{uf.piso}° {uf.departamento or ''}".strip(), est["small"]),
            Paragraph(escape(propietario), est["small"]),
            Paragraph(f"{detalle.alicuota:.2f}", est["num"]),
            Paragraph(_money(detalle.monto_ordinario), est["num"]),
            Paragraph(_money(detalle.monto_extraordinario), est["num"]),
            *([Paragraph(_money(detalle.monto_fondo_reserva), est["num"])] if con_fondo else []),
            Paragraph(_money(detalle.monto_total), est["num_b"]),
        ])
        total_ord += detalle.monto_ordinario
        total_ext += detalle.monto_extraordinario
        total_gen += detalle.monto_total

    filas.append([
        Paragraph("", est["small"]),
        Paragraph("", est["small"]),
        Paragraph("TOTAL", est["bold"]),
        Paragraph("100.00", est["th"]),
        Paragraph(_money(total_ord), est["num_b"]),
        Paragraph(_money(total_ext), est["num_b"]),
        *([Paragraph(_money(liquidacion.total_fondo_reserva), est["num_b"])] if con_fondo else []),
        Paragraph(_money(total_gen), est["num_b"]),
    ])

    anchos = [30, 45, 120, 45, 75, 75, 70, 85] if con_fondo else [30, 45, 180, 45, 80, 80, 85]
    tabla = Table(filas, colWidths=anchos, repeatRows=1)
    ultima = len(filas) - 1
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, ultima), (-1, ultima), GRIS_TOTAL),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return tabla


def _periodo(periodo):
    anio, _, mes = (periodo or "").partition("-")
    return f"{MESES.get(mes, mes)} {anio}".strip()


def generar_recibo_pago_pdf(pago):
    est = _estilos()
    detalle = pago.detalle_liquidacion
    uf = detalle.unidad_funcional
    consorcio = detalle.liquidacion.consorcio
    usuario = uf.propietario.usuario
    unidad = f"Piso {uf.piso}" + (f" · Depto. {uf.departamento}" if uf.departamento else "")

    banner = Table([
        [Paragraph("RECIBO DE PAGO", est["banner_t"])],
        [Paragraph(f"N° {pago.pk:08d} · Expensas {escape(consorcio.nombre)}", est["banner_p"])],
    ], colWidths=[ANCHO_UTIL])
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AZUL),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    datos = [
        ("Consorcio", f"{_txt(consorcio.nombre)} · CUIT {_txt(consorcio.cuit)}"),
        ("Domicilio", f"{_txt(consorcio.calle)} {_txt(consorcio.altura)}"),
        ("Unidad funcional", _txt(unidad)),
        ("Propietario", _txt(usuario.get_full_name() or usuario.username)),
        ("Fecha de pago", _fecha(pago.fecha_pago)),
        ("Período informado", _periodo(detalle.liquidacion.periodo)),
    ]
    tabla_datos = Table(
        [[Paragraph(etiqueta, est["bold"]), Paragraph(valor, est["normal"])] for etiqueta, valor in datos],
        colWidths=[ANCHO_UTIL * 0.3, ANCHO_UTIL * 0.7],
    )
    tabla_datos.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, BORDE),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    filas = [[Paragraph("Período", est["th_left"]), Paragraph("Concepto", est["th_left"]),
              Paragraph("Importe", est["th"])]]
    for imputacion in pago.imputaciones.select_related("detalle_liquidacion__liquidacion"):
        periodo = _periodo(imputacion.detalle_liquidacion.liquidacion.periodo) if imputacion.detalle_liquidacion else "-"
        filas.append([Paragraph(periodo, est["normal"]), Paragraph(imputacion.get_concepto_display(), est["normal"]),
                      Paragraph(_money(imputacion.monto), est["num"])])
    filas.append([Paragraph("TOTAL RECIBIDO", est["bold"]), "", Paragraph(_money(pago.monto_pagado), est["num_b"])])
    tabla_imputacion = Table(filas, colWidths=[ANCHO_UTIL * 0.35, ANCHO_UTIL * 0.4, ANCHO_UTIL * 0.25])
    tabla_imputacion.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GRIS_HEADER),
        ("BACKGROUND", (0, -1), (-1, -1), GRIS_TOTAL),
        ("SPAN", (0, -1), (1, -1)),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDE),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    story = [
        banner, Spacer(1, 6 * mm), tabla_datos, Spacer(1, 6 * mm),
        Paragraph("Imputación del pago", est["titulo"]),
        Paragraph("El pago cancela primero los intereses y después el capital, del período más viejo al más nuevo.",
                  est["small"]),
        Spacer(1, 2 * mm), tabla_imputacion, Spacer(1, 8 * mm),
        Paragraph("Pago validado por la administración del consorcio.", est["small"]),
    ]
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=15 * mm,
        title=f"Recibo de pago {pago.pk:08d}",
    )
    doc.build(story)
    return buffer.getvalue()


def _tabla_resumen_caja(liquidacion, est):
    from django.db.models import Sum
    from datetime import date
    from .models import MovimientoCaja

    anio, mes = liquidacion.periodo.split('-')
    fecha_inicio = date(int(anio), int(mes), 1)
    fecha_fin = liquidacion.fecha_cierre or date.today()

    movs = MovimientoCaja.objects.filter(consorcio=liquidacion.consorcio)

    s_ini = movs.filter(fecha__lt=fecha_inicio).aggregate(t=Sum('monto'))['t'] or Decimal('0')
    s_fin = movs.filter(fecha__lte=fecha_fin).aggregate(t=Sum('monto'))['t'] or Decimal('0')

    periodo_movs = movs.filter(fecha__gte=fecha_inicio, fecha__lte=fecha_fin)
    ing = periodo_movs.filter(monto__gt=0)
    egr = periodo_movs.filter(monto__lt=0)

    def get_sum(qs):
        return qs.aggregate(t=Sum('monto'))['t'] or Decimal('0')

    i_ord = get_sum(ing.filter(tipo='ordinario'))
    i_ext = get_sum(ing.filter(tipo='extraordinario'))
    i_efvo = get_sum(ing.filter(medio_pago='efectivo'))
    i_trans = get_sum(ing.filter(medio_pago='transferencia'))
    i_total = i_ord + i_ext

    e_ord = abs(get_sum(egr.filter(tipo='ordinario')))
    e_ext = abs(get_sum(egr.filter(tipo='extraordinario')))
    e_efvo = abs(get_sum(egr.filter(medio_pago='efectivo')))
    e_trans = abs(get_sum(egr.filter(medio_pago='transferencia')))
    e_total = e_ord + e_ext

    encabezado = [
        Paragraph("Resumen de Caja (Movimientos del mes)", est["th_left"]),
        Paragraph("Ordinario", est["th"]),
        Paragraph("Extraordinario", est["th"]),
        Paragraph("Efectivo", est["th"]),
        Paragraph("Transferencia", est["th"]),
        Paragraph("Total", est["th"]),
    ]

    filas = [
        encabezado,
        [
            Paragraph("<b>Ingresos del mes</b>", est["normal"]),
            Paragraph(_money(i_ord), est["num"]),
            Paragraph(_money(i_ext), est["num"]),
            Paragraph(_money(i_efvo), est["num"]),
            Paragraph(_money(i_trans), est["num"]),
            Paragraph(_money(i_total), est["num_b"]),
        ],
        [
            Paragraph("<b>Egresos del mes</b>", est["normal"]),
            Paragraph(_money(e_ord), est["num"]),
            Paragraph(_money(e_ext), est["num"]),
            Paragraph(_money(e_efvo), est["num"]),
            Paragraph(_money(e_trans), est["num"]),
            Paragraph(_money(e_total), est["num_b"]),
        ],
        [
            Paragraph(f"<b>Saldo Inicial (al {fecha_inicio.strftime('%d/%m/%Y')})</b>", est["normal"]),
            "", "", "", "",
            Paragraph(_money(s_ini), est["num_b"]),
        ],
        [
            Paragraph(f"<b>Saldo Final (al {fecha_fin.strftime('%d/%m/%Y')})</b>", est["normal"]),
            "", "", "", "",
            Paragraph(_money(s_fin), est["num_b"]),
        ]
    ]

    anchos = [ANCHO_UTIL * 0.30, ANCHO_UTIL * 0.13, ANCHO_UTIL * 0.14, ANCHO_UTIL * 0.13, ANCHO_UTIL * 0.15, ANCHO_UTIL * 0.15]
    
    tabla = Table(filas, colWidths=anchos)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GRIS_HEADER),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("SPAN", (0, 3), (4, 3)), 
        ("SPAN", (0, 4), (4, 4)), 
        ("BACKGROUND", (0, 3), (-1, 3), GRIS_SUBTOTAL),
        ("BACKGROUND", (0, 4), (-1, 4), GRIS_TOTAL),
    ]))
    return tabla
