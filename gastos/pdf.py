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


def _tabla_subtipo(nombre_subtipo, gastos, nombres_grupos, est):
    """Una tabla por subtipo. Solo muestra los grupos que ese subtipo usa."""
    ids_usados = sorted({g.grupo_id for g in gastos}, key=lambda x: (x is None, x))
    columnas = len(ids_usados)
    anchos = _anchos(columnas)

    encabezado_grupos = [Paragraph(escape(nombres_grupos.get(i, "Sin grupo")), est["th"]) for i in ids_usados]
    filas = [
        [Paragraph(escape(nombre_subtipo), est["subtipo"])] + [""] * columnas,
        [Paragraph("Concepto / Detalle", est["th_left"])] + encabezado_grupos,
    ]

    subtotales = {i: Decimal("0.00") for i in ids_usados}
    for gasto in gastos:
        fila = [Paragraph(escape(gasto.concepto or "(Sin concepto)"), est["normal"])]
        for i in ids_usados:
            if gasto.grupo_id == i:
                subtotales[i] += gasto.monto
                fila.append(Paragraph(_money(gasto.monto), est["num_b"]))
            else:
                fila.append(Paragraph("-", est["th"]))
        filas.append(fila)

    filas.append(
        [Paragraph(f"SUBTOTAL {escape(nombre_subtipo)}:", est["bold"])]
        + [Paragraph(_money(subtotales[i]), est["num_b"]) for i in ids_usados]
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
    return tabla, subtotales


def _tabla_total_general(totales, nombres_grupos, est):
    ids = sorted(totales.keys(), key=lambda x: (x is None, x))
    anchos = _anchos(len(ids))
    fila = [Paragraph("TOTAL ESTIMADO GENERAL:", est["bold"])] + [
        Paragraph(_money(totales[i]), est["num_b"]) for i in ids
    ]
    encabezado = [Paragraph("", est["th_left"])] + [
        Paragraph(escape(nombres_grupos.get(i, "Sin grupo")), est["th"]) for i in ids
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


def generar_pdf_liquidacion(liquidacion, gastos, admin=None):
    """
    liquidacion : instancia de Liquidacion (con .consorcio)
    gastos      : iterable de Gasto (con .grupo_id, .concepto, .monto, .subtipo)
    admin       : dict con las claves admin_razon, admin_nombre, ... (opcional)
    Devuelve los bytes del PDF.
    """
    est = _estilos()
    gastos = list(gastos)

    nombres_grupos = {}
    for g in gastos:
        if g.grupo_id is not None:
            nombres_grupos[g.grupo_id] = g.grupo.nombre

    por_subtipo = OrderedDict()
    for g in gastos:
        clave = (getattr(g, "subtipo", "") or "").strip().upper() or "GASTOS GENERALES"
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
    if not por_subtipo:
        story.append(Paragraph("Sin gastos ingresados.", est["normal"]))
    else:
        for nombre, lista in por_subtipo.items():
            tabla, subtotales = _tabla_subtipo(nombre, lista, nombres_grupos, est)
            story.append(tabla)
            story.append(Spacer(1, 4 * mm))
            for gid, valor in subtotales.items():
                totales[gid] = totales.get(gid, Decimal("0.00")) + valor
        story.append(_tabla_total_general(totales, nombres_grupos, est))

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=15 * mm,
        title=f"Liquidación {liquidacion.periodo} - {liquidacion.consorcio.nombre}",
    )
    doc.build(story)
    return buffer.getvalue()