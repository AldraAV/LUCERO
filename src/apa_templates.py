"""
apa_templates.py — Plantillas XML para estructuras APA 7ª edición.
Cada función devuelve un fragmento OOXML listo para inyectar con lxml.
"""

from __future__ import annotations

from lxml import etree

from .utils import NS, get_logger

log = get_logger("aldradoc.apa")

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS INTERNOS
# ─────────────────────────────────────────────────────────────────────────────

def _w(tag: str) -> str:
    return f"{{{NS['w']}}}{tag}"


def _make_run(text: str, bold: bool = False, italic: bool = False,
              font_size_half: int = 24) -> etree._Element:
    """Crea un <w:r> con formato básico según APA 7 (Times New Roman 12pt) y orden canónico OOXML en rPr."""
    run = etree.Element(_w("r"))
    rpr = etree.SubElement(run, _w("rPr"))
    
    # 1. rFonts DEBE ir antes de b, i, sz en el esquema OOXML
    rFonts = etree.SubElement(rpr, _w("rFonts"))
    rFonts.set(_w("ascii"), "Times New Roman")
    rFonts.set(_w("hAnsi"), "Times New Roman")
    rFonts.set(_w("cs"), "Times New Roman")

    # 2. b e i
    if bold:
        etree.SubElement(rpr, _w("b"))
    if italic:
        etree.SubElement(rpr, _w("i"))

    # 3. sz y szCs
    sz = etree.SubElement(rpr, _w("sz"))
    sz.set(_w("val"), str(font_size_half))
    sz_cs = etree.SubElement(rpr, _w("szCs"))
    sz_cs.set(_w("val"), str(font_size_half))

    t = etree.SubElement(run, _w("t"))
    t.text = text
    if text.startswith(" ") or text.endswith(" "):
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    return run


def _make_para(style_id: str, indent_left: int = 0,
               hanging: int = 0) -> etree._Element:
    """Crea un <w:p> con estilo y sangría configurados."""
    para = etree.Element(_w("p"))
    ppr = etree.SubElement(para, _w("pPr"))
    ps = etree.SubElement(ppr, _w("pStyle"))
    ps.set(_w("val"), style_id)
    if indent_left or hanging:
        ind = etree.SubElement(ppr, _w("ind"))
        if indent_left:
            ind.set(_w("left"), str(indent_left))
        if hanging:
            ind.set(_w("hanging"), str(hanging))
    return para


# ─────────────────────────────────────────────────────────────────────────────
# PLANTILLAS APA 7ª
# ─────────────────────────────────────────────────────────────────────────────

def apa_heading1(text: str) -> etree._Element:
    """
    Encabezado Nivel 1 APA 7ª:
    Centrado, negrita, sin cursiva, Title Case.
    """
    para = etree.Element(_w("p"))
    ppr = etree.SubElement(para, _w("pPr"))
    ps = etree.SubElement(ppr, _w("pStyle"))
    ps.set(_w("val"), "Heading1")
    jc = etree.SubElement(ppr, _w("jc"))
    jc.set(_w("val"), "center")
    spacing = etree.SubElement(ppr, _w("spacing"))
    spacing.set(_w("line"), "480")
    spacing.set(_w("lineRule"), "auto")
    spacing.set(_w("after"), "0")
    para.append(_make_run(text, bold=True))
    log.debug("apa_heading1 generado: %r", text)
    return para


def apa_heading2(text: str) -> etree._Element:
    """
    Encabezado Nivel 2 APA 7ª:
    Alineado a la izquierda, negrita, sin cursiva.
    """
    para = etree.Element(_w("p"))
    ppr = etree.SubElement(para, _w("pPr"))
    ps = etree.SubElement(ppr, _w("pStyle"))
    ps.set(_w("val"), "Heading2")
    jc = etree.SubElement(ppr, _w("jc"))
    jc.set(_w("val"), "left")
    spacing = etree.SubElement(ppr, _w("spacing"))
    spacing.set(_w("line"), "480")
    spacing.set(_w("lineRule"), "auto")
    spacing.set(_w("after"), "0")
    para.append(_make_run(text, bold=True))
    log.debug("apa_heading2 generado: %r", text)
    return para


def apa_heading3(text: str) -> etree._Element:
    """
    Encabezado Nivel 3 APA 7ª:
    Alineado a la izquierda, negrita, cursiva.
    """
    para = etree.Element(_w("p"))
    ppr = etree.SubElement(para, _w("pPr"))
    ps = etree.SubElement(ppr, _w("pStyle"))
    ps.set(_w("val"), "Heading3")
    jc = etree.SubElement(ppr, _w("jc"))
    jc.set(_w("val"), "left")
    spacing = etree.SubElement(ppr, _w("spacing"))
    spacing.set(_w("line"), "480")
    spacing.set(_w("lineRule"), "auto")
    spacing.set(_w("after"), "0")
    para.append(_make_run(text, bold=True, italic=True))
    log.debug("apa_heading3 generado: %r", text)
    return para


def apa_heading4(text: str) -> etree._Element:
    """
    Encabezado Nivel 4 APA 7ª:
    Alineado con sangría de 1.27 cm (0.5 pulg = 720 twips), negrita,
    finaliza con punto.
    """
    txt = text.strip()
    if not txt.endswith("."):
        txt += "."
    para = etree.Element(_w("p"))
    ppr = etree.SubElement(para, _w("pPr"))
    ps = etree.SubElement(ppr, _w("pStyle"))
    ps.set(_w("val"), "Heading4")
    ind = etree.SubElement(ppr, _w("ind"))
    ind.set(_w("firstLine"), "720")
    spacing = etree.SubElement(ppr, _w("spacing"))
    spacing.set(_w("line"), "480")
    spacing.set(_w("lineRule"), "auto")
    spacing.set(_w("after"), "0")
    para.append(_make_run(txt, bold=True))
    log.debug("apa_heading4 generado: %r", txt)
    return para


def apa_heading5(text: str) -> etree._Element:
    """
    Encabezado Nivel 5 APA 7ª:
    Alineado con sangría de 1.27 cm (0.5 pulg = 720 twips), negrita y cursiva,
    finaliza con punto.
    """
    txt = text.strip()
    if not txt.endswith("."):
        txt += "."
    para = etree.Element(_w("p"))
    ppr = etree.SubElement(para, _w("pPr"))
    ps = etree.SubElement(ppr, _w("pStyle"))
    ps.set(_w("val"), "Heading5")
    ind = etree.SubElement(ppr, _w("ind"))
    ind.set(_w("firstLine"), "720")
    spacing = etree.SubElement(ppr, _w("spacing"))
    spacing.set(_w("line"), "480")
    spacing.set(_w("lineRule"), "auto")
    spacing.set(_w("after"), "0")
    para.append(_make_run(txt, bold=True, italic=True))
    log.debug("apa_heading5 generado: %r", txt)
    return para


def apa_centered_text(text: str, bold: bool = False, italic: bool = False) -> etree._Element:
    """
    Párrafo de texto centrado (portadas y títulos iniciales APA):
    Centrado, doble espacio, Times New Roman 12pt.
    """
    para = etree.Element(_w("p"))
    ppr = etree.SubElement(para, _w("pPr"))
    jc = etree.SubElement(ppr, _w("jc"))
    jc.set(_w("val"), "center")
    spacing = etree.SubElement(ppr, _w("spacing"))
    spacing.set(_w("line"), "480")
    spacing.set(_w("lineRule"), "auto")
    spacing.set(_w("after"), "0")
    para.append(_make_run(text, bold=bold, italic=italic))
    log.debug("apa_centered_text generado: %r", text)
    return para


def apa_page_break() -> etree._Element:
    """Inserta un salto de página formal OOXML."""
    para = etree.Element(_w("p"))
    run = etree.SubElement(para, _w("r"))
    br = etree.SubElement(run, _w("br"))
    br.set(_w("type"), "page")
    log.debug("apa_page_break generado")
    return para


def apa_body_paragraph(text: str, first_line_indent: int = 720) -> etree._Element:
    """
    Párrafo de cuerpo APA 7ª:
    Sangría de primera línea 1.27 cm (720 twips), alineado a la izquierda, Times New Roman 12pt.
    """
    para = etree.Element(_w("p"))
    ppr = etree.SubElement(para, _w("pPr"))
    ps = etree.SubElement(ppr, _w("pStyle"))
    ps.set(_w("val"), "Normal")
    ind = etree.SubElement(ppr, _w("ind"))
    ind.set(_w("firstLine"), str(first_line_indent))
    jc = etree.SubElement(ppr, _w("jc"))
    jc.set(_w("val"), "left")
    spacing = etree.SubElement(ppr, _w("spacing"))
    spacing.set(_w("line"), "480")       # Doble espacio = 24pt = 480 twips
    spacing.set(_w("lineRule"), "auto")
    spacing.set(_w("after"), "0")
    para.append(_make_run(text))
    log.debug("apa_body_paragraph generado (%d chars)", len(text))
    return para


def apa_figure_label(number: int, title: str) -> list[etree._Element]:
    """
    Bloque APA 7ª para etiqueta de figura:
    Línea 1: 'Figura N' (negrita)
    Línea 2: título en cursiva
    Ambas sin sangría de primera línea.
    """
    p_num = etree.Element(_w("p"))
    ppr1 = etree.SubElement(p_num, _w("pPr"))
    ind1 = etree.SubElement(ppr1, _w("ind"))
    ind1.set(_w("firstLine"), "0")
    spacing1 = etree.SubElement(ppr1, _w("spacing"))
    spacing1.set(_w("line"), "480")
    spacing1.set(_w("lineRule"), "auto")
    spacing1.set(_w("after"), "0")
    p_num.append(_make_run(f"Figura {number}", bold=True))

    p_title = etree.Element(_w("p"))
    ppr2 = etree.SubElement(p_title, _w("pPr"))
    ind2 = etree.SubElement(ppr2, _w("ind"))
    ind2.set(_w("firstLine"), "0")
    spacing2 = etree.SubElement(ppr2, _w("spacing"))
    spacing2.set(_w("line"), "480")
    spacing2.set(_w("lineRule"), "auto")
    spacing2.set(_w("after"), "0")
    p_title.append(_make_run(title, italic=True))

    log.debug("apa_figure_label Figura %d generado", number)
    return [p_num, p_title]


def apa_figure_note(note_text: str) -> etree._Element:
    """
    Nota de figura APA 7ª:
    'Nota.' en cursiva seguido del texto de la nota, sin sangría.
    """
    para = etree.Element(_w("p"))
    ppr = etree.SubElement(para, _w("pPr"))
    ind = etree.SubElement(ppr, _w("ind"))
    ind.set(_w("firstLine"), "0")
    spacing = etree.SubElement(ppr, _w("spacing"))
    spacing.set(_w("line"), "480")
    spacing.set(_w("lineRule"), "auto")
    spacing.set(_w("after"), "0")
    para.append(_make_run("Nota. ", italic=True))
    para.append(_make_run(note_text))
    log.debug("apa_figure_note generado")
    return para


def apa_reference_entry(text: str, cursiva: str | None = None) -> etree._Element:
    """
    Entrada de referencia APA 7ª:
    Sangría francesa (hanging indent) de 1.27 cm = 720 twips, doble espacio.
    Si se especifica 'cursiva', esa subcadena se formatea en cursiva.
    """
    para = etree.Element(_w("p"))
    ppr = etree.SubElement(para, _w("pPr"))
    ps = etree.SubElement(ppr, _w("pStyle"))
    ps.set(_w("val"), "Normal")
    ind = etree.SubElement(ppr, _w("ind"))
    ind.set(_w("left"), "720")
    ind.set(_w("hanging"), "720")
    spacing = etree.SubElement(ppr, _w("spacing"))
    spacing.set(_w("line"), "480")
    spacing.set(_w("lineRule"), "auto")
    spacing.set(_w("after"), "0")

    if cursiva and cursiva in text:
        partes = text.split(cursiva, 1)
        if partes[0]:
            para.append(_make_run(partes[0]))
        para.append(_make_run(cursiva, italic=True))
        if partes[1]:
            para.append(_make_run(partes[1]))
    else:
        para.append(_make_run(text))

    log.debug("apa_reference_entry generado: %r", text[:60])
    return para


def apa_in_text_citation(author: str, year: int,
                          page: str | None = None) -> str:
    """
    Retorna el string de cita en texto APA 7ª.
    Ej: (García, 2022) o (García, 2022, p. 45)
    """
    base = f"({author}, {year}"
    if page:
        base += f", p. {page}"
    return base + ")"


def apa_header_page_number() -> etree._Element:
    """
    Genera el bloque OOXML de encabezado APA 7:
    Alineado a la derecha, Times New Roman 12pt, campo PAGE dinámico.
    """
    hdr = etree.Element(_w("hdr"))
    para = etree.SubElement(hdr, _w("p"))
    ppr = etree.SubElement(para, _w("pPr"))
    ps = etree.SubElement(ppr, _w("pStyle"))
    ps.set(_w("val"), "Header")
    jc = etree.SubElement(ppr, _w("jc"))
    jc.set(_w("val"), "right")

    fld = etree.SubElement(para, _w("fldSimple"))
    fld.set(_w("instr"), "PAGE")
    r = etree.SubElement(fld, _w("r"))
    rpr = etree.SubElement(r, _w("rPr"))
    rFonts = etree.SubElement(rpr, _w("rFonts"))
    rFonts.set(_w("ascii"), "Times New Roman")
    rFonts.set(_w("hAnsi"), "Times New Roman")
    sz = etree.SubElement(rpr, _w("sz"))
    sz.set(_w("val"), "24")
    t = etree.SubElement(r, _w("t"))
    t.text = "1"
    return hdr


# ─────────────────────────────────────────────────────────────────────────────
# CATÁLOGO DE PLANTILLAS
# ─────────────────────────────────────────────────────────────────────────────
TEMPLATE_CATALOG: dict[str, str] = {
    "heading1":       "Encabezado Nivel 1 — centrado, negrita",
    "heading2":       "Encabezado Nivel 2 — izquierda, negrita",
    "heading3":       "Encabezado Nivel 3 — izquierda, negrita cursiva",
    "heading4":       "Encabezado Nivel 4 — sangría 1.27cm, negrita, punto final",
    "heading5":       "Encabezado Nivel 5 — sangría 1.27cm, negrita cursiva, punto final",
    "body_paragraph": "Párrafo cuerpo — sangría 1.27cm, doble espacio",
    "figure_label":   "Etiqueta de figura — número negrita + título cursiva",
    "figure_note":    "Nota de figura — 'Nota.' cursiva + texto",
    "reference":      "Referencia — sangría francesa 1.27cm, soporte cursiva",
    "centered_text":  "Texto centrado — útil para portada, doble espacio",
    "page_break":     "Salto de página formal OOXML",
    "header_page":    "Encabezado APA 7 — número de página alineado a la derecha",
}
