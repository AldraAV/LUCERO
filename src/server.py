"""
server.py — Servidor MCP principal: LUCERO
Expone las herramientas quirúrgicas como Tools MCP usando FastMCP.
"""

from __future__ import annotations

# ── CRITICAL: Configurar structlog a stderr ANTES de cualquier import ────────
# El protocolo MCP usa stdout para JSON-RPC. Cualquier texto no-JSON en stdout
# rompe clientes como Opencode con "Unexpected non-whitespace character after JSON".
import sys

import structlog

structlog.configure(
    logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
)
# ─────────────────────────────────────────────────────────────────────────────

import json
from pathlib import Path
from typing import Annotated, Any

from mcp.server.fastmcp import Context, FastMCP

from src.apa_templates import (
    TEMPLATE_CATALOG,
    apa_body_paragraph,
    apa_centered_text,
    apa_figure_label,
    apa_figure_note,
    apa_heading1,
    apa_heading2,
    apa_heading3,
    apa_heading4,
    apa_heading5,
    apa_page_break,
    apa_reference_entry,
)
from src.surgeon import DocxSurgeon
from src.utils import get_logger, qn

log = get_logger("lucero.server")

from src.utils import export_toon


def _custom_dumps(obj, *args, **kwargs):
    return export_toon(obj)

json.dumps = _custom_dumps


# ─────────────────────────────────────────────────────────────────────────────
# INSTANCIA MCP
# ─────────────────────────────────────────────────────────────────────────────
mcp = FastMCP(
    name="LUCERO",
    instructions=(
        "Servidor MCP de manipulacion quirurgica de documentos (DOCX, PPTX y XLSX).\n"
        "Opera directamente sobre el XML interno (ECMA-376) usando XPath\n"
        "para garantizar precision de nodo y zero format loss.\n\n"
        "Flujo recomendado:\n"
        "1. inspect_xml_tree  → Ver estructura real del documento\n"
        "2. surgical_replace  → Cambiar texto sin tocar el formato\n"
        "3. inject_apa_structure → Insertar bloques académicos APA 7\n"
        "4. commit_changes    → Guardar el DOCX final sin corromperlo\n"
    ),
)

# ─────────────────────────────────────────────────────────────────────────────
# TOOL 1: inspect_xml_tree
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def inspect_xml_tree(
    docx_path: Annotated[str, "Ruta absoluta al archivo .docx a inspeccionar"],
    max_paragraphs: Annotated[int, "Máximo de párrafos a devolver (default 100)"] = 100,
    style_filter: Annotated[str | None, "Filtrar por ID de estilo (ej. 'Heading1', 'ParrafoAPA')"] = None,
) -> str:
    """
    Devuelve el mapa estructural completo del documento:
    cada párrafo con su paraId, estilo, texto completo y los runs individuales
    con su formato (bold, italic, underline, strike) y XPath exacto.

    Esto permite que el LLM 'vea' la estructura oculta antes de operar.
    """
    log.info("[TOOL] inspect_xml_tree: %s (max=%d, filter=%s)",
             docx_path, max_paragraphs, style_filter)
    try:
        surgeon = DocxSurgeon(docx_path)
        data = surgeon.inspect_tree(max_paragraphs=max_paragraphs)

        if style_filter:
            data = [p for p in data if p.get("style") == style_filter]
            log.info("Filtrado por estilo '%s': %d párrafos", style_filter, len(data))

        styles = surgeon.get_styles_list()

        result = {
            "file": Path(docx_path).name,
            "total_paragraphs_scanned": len(data),
            "styles_used": styles,
            "paragraphs": data,
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as exc:
        log.error("[TOOL ERROR] inspect_xml_tree: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 2: surgical_replace
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def surgical_replace(
    docx_path: Annotated[str, "Ruta al .docx a operar"],
    target_text: Annotated[str, "Texto exacto a localizar en los nodos <w:t>"],
    replacement_text: Annotated[str, "Texto de reemplazo (el formato del run se preserva)"],
    output_path: Annotated[str | None, "Ruta de salida. Si es None sobreescribe el original"] = None,
    occurrence: Annotated[int, "Qué aparición reemplazar: 1=primera, -1=todas"] = 1,
) -> str:
    """
    Localiza 'target_text' en el XML interno mediante XPath y reemplaza
    SOLO el contenido del nodo <w:t>, dejando intactas las etiquetas de
    formato <w:rPr> que lo rodean (negrita, color, tamaño, etc.).

    Maneja automáticamente texto fragmentado entre múltiples runs consecutivos
    (comportamiento habitual del autocorrector de Word).

    Al terminar, hace commit automático del DOCX.
    """
    log.info("[TOOL] surgical_replace: %r → %r en %s",
             target_text, replacement_text, docx_path)
    try:
        surgeon = DocxSurgeon(docx_path)
        replace_result = surgeon.surgical_replace(
            target_text=target_text,
            replacement_text=replacement_text,
            occurrence=occurrence,
        )

        if replace_result["occurrences_replaced"] == 0:
            return json.dumps({
                "success": False,
                "reason": f"No se encontró '{target_text}' en el documento.",
                "detail": replace_result,
            }, ensure_ascii=False, indent=2)

        commit_result = surgeon.commit_changes(output_path)

        return json.dumps({
            "success":      True,
            "replace":      replace_result,
            "commit":       commit_result,
        }, ensure_ascii=False, indent=2)

    except Exception as exc:
        log.error("[TOOL ERROR] surgical_replace: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 3: inject_apa_structure
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def inject_apa_structure(
    docx_path: Annotated[str, "Ruta al .docx objetivo"],
    anchor_text: Annotated[str, "Texto del párrafo de anclaje para la inyección"],
    template_type: Annotated[str, (
        "Tipo de bloque APA a inyectar. Opciones: "
        "'heading1', 'heading2', 'heading3', 'body_paragraph', "
        "'figure_label', 'figure_note', 'reference'"
    )],
    content: Annotated[str, "Texto principal del bloque a inyectar"],
    position: Annotated[str, "'before', 'after' o 'replace'"] = "after",
    output_path: Annotated[str | None, "Ruta de salida (None = sobreescribir)"] = None,
    # Parámetros opcionales para plantillas específicas
    figure_number: Annotated[int | None, "Solo para 'figure_label': número de figura"] = None,
    note_text: Annotated[str | None, "Solo para 'figure_note': texto de la nota"] = None,
) -> str:
    """
    Inyecta un bloque de estructura APA 7ª (encabezado, párrafo, etiqueta de figura,
    nota, referencia) en la posición exacta indicada por 'anchor_text'.

    Todos los bloques se generan como XML OOXML nativo — no como texto plano —
    lo que garantiza compatibilidad completa con Word y las normas APA 7ª.

    Catálogo de templates disponibles (llama a list_apa_templates para ver descripciones):
    heading1, heading2, heading3, body_paragraph, figure_label, figure_note, reference
    """
    log.info("[TOOL] inject_apa_structure: template=%s, anchor=%r, position=%s",
             template_type, anchor_text, position)
    try:
        from lxml import etree as _etree

        # Seleccionar y construir los nodos según el template
        nodes: list[_etree._Element] = []

        match template_type:
            case "heading1":
                nodes = [apa_heading1(content)]
            case "heading2":
                nodes = [apa_heading2(content)]
            case "heading3":
                nodes = [apa_heading3(content)]
            case "heading4":
                nodes = [apa_heading4(content)]
            case "heading5":
                nodes = [apa_heading5(content)]
            case "body_paragraph":
                nodes = [apa_body_paragraph(content)]
            case "figure_label":
                num = figure_number or 1
                nodes = apa_figure_label(num, content)
            case "figure_note":
                note = note_text or content
                nodes = [apa_figure_note(note)]
            case "reference":
                nodes = [apa_reference_entry(content)]
            case "centered_text":
                nodes = [apa_centered_text(content)]
            case "page_break":
                nodes = [apa_page_break()]
            case _:
                available = list(TEMPLATE_CATALOG.keys())
                return json.dumps({
                    "error": f"Template '{template_type}' no existe.",
                    "available": available,
                }, ensure_ascii=False)

        surgeon = DocxSurgeon(docx_path)
        inject_result = surgeon.inject_apa_structure(
            anchor_text=anchor_text,
            nodes=nodes,
            position=position,
        )

        if not inject_result.get("success"):
            return json.dumps(inject_result, ensure_ascii=False, indent=2)

        commit_result = surgeon.commit_changes(output_path)

        return json.dumps({
            "success":  True,
            "template": template_type,
            "inject":   inject_result,
            "commit":   commit_result,
        }, ensure_ascii=False, indent=2)

    except Exception as exc:
        log.error("[TOOL ERROR] inject_apa_structure: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 4: commit_changes (explícito, para flujos manuales)
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def commit_changes(
    docx_path: Annotated[str, "Ruta al .docx con cambios pendientes en memoria"],
    output_path: Annotated[str | None, "Ruta destino. None = sobreescribir el original"] = None,
) -> str:
    """
    Reempaqueta el DOCX asegurando que [Content_Types].xml, todas las
    relaciones, imágenes y metadatos se mantengan íntegros.

    Solo sobreescribe word/document.xml con los cambios quirúrgicos.
    El resto del ZIP se copia byte a byte desde el original.

    Úsalo cuando hayas realizado múltiples operaciones quirúrgicas y quieras
    consolidar todo en un único commit al final (flujo batch).
    """
    log.info("[TOOL] commit_changes: %s → %s", docx_path, output_path or "(in-place)")
    try:
        surgeon = DocxSurgeon(docx_path)
        # Marcar dirty para forzar el commit aunque no haya cambios en memoria
        # (útil cuando el XML fue modificado externamente)
        surgeon._dirty = True
        result = surgeon.commit_changes(output_path)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] commit_changes: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 5: list_apa_templates  (descubrimiento)
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_apa_templates() -> str:
    """
    Devuelve el catálogo completo de plantillas APA 7ª disponibles
    para inject_apa_structure, con su descripción y parámetros especiales.
    """
    catalog_out = {
        k: {
            "description": v,
            "extra_params": _EXTRA_PARAMS.get(k, {}),
        }
        for k, v in TEMPLATE_CATALOG.items()
    }
    return json.dumps(catalog_out, ensure_ascii=False, indent=2)


_EXTRA_PARAMS: dict[str, dict] = {
    "figure_label": {"figure_number": "int — número de figura (ej. 3)"},
    "figure_note":  {"note_text": "str — puede diferir de 'content'"},
}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 6: run_xpath  (poder bruto para operaciones avanzadas)
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def run_xpath(
    docx_path: Annotated[str, "Ruta al .docx"],
    xpath_expr: Annotated[str, "Expresión XPath usando prefijos w:, w14:, r:, etc."],
) -> str:
    """
    Ejecuta una expresión XPath arbitraria sobre el document.xml y devuelve
    los resultados como lista de tags legibles con su texto y atributos.

    Útil para exploración avanzada y diagnóstico quirúrgico.

    Ejemplos de XPath útiles:
    - '//w:p[@w14:paraId]'                    → párrafos con paraId
    - '//w:r[w:rPr/w:b]//w:t'               → runs en negrita
    - '//w:pStyle[@w:val="Heading1"]/..'     → párrafos con Heading1
    - '//w:t[contains(text(), "Conclusión")]' → texto que contiene "Conclusión"
    """
    log.info("[TOOL] run_xpath: %s", xpath_expr)
    try:
        surgeon = DocxSurgeon(docx_path)
        nodes = surgeon.find_by_xpath(xpath_expr)

        results = []
        for node in nodes[:50]:   # limitar salida a 50 nodos
            text = node.text or ""
            tag  = node.tag
            attrs = dict(node.attrib)
            results.append({
                "tag":   tag,
                "text":  text,
                "attrs": attrs,
            })

        return json.dumps({
            "xpath":        xpath_expr,
            "total_found":  len(nodes),
            "shown":        len(results),
            "results":      results,
        }, ensure_ascii=False, indent=2)

    except Exception as exc:
        log.error("[TOOL ERROR] run_xpath: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 7: surgical_style_edit  (Full Format Control)
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def surgical_style_edit(
    docx_path: Annotated[str, "Ruta al .docx a operar"],
    xpath_expr: Annotated[str, "XPath exacto del párrafo (w:p) o run (w:r) a modificar"],
    properties: Annotated[dict, "JSON con propiedades a aplicar (align, size, font, bold, italic, indent_left, indent_hanging)"],
    output_path: Annotated[str | None, "Ruta de salida. Si es None sobreescribe el original"] = None,
) -> str:
    """
    Inyecta o modifica propiedades de estilo avanzadas (OOXML) directamente en el 
    árbol XML en la ubicación indicada por XPath, creando los nodos necesarios
    (w:pPr, w:rPr) si no existen, sin tocar el texto.
    
    properties debe ser un diccionario que soporte las claves:
    - align (str): 'left', 'center', 'right', 'both'
    - size (int): tamaño de fuente en medios puntos (ej. 24 para 12pt)
    - font (str): nombre de la fuente (ej. 'Arial')
    - bold (bool): True/False
    - italic (bool): True/False
    - indent_left (int): sangría izquierda en twips (1 cm = ~567 twips)
    - indent_hanging (int): sangría francesa en twips
    """
    log.info("[TOOL] surgical_style_edit: %s", xpath_expr)
    try:
        surgeon = DocxSurgeon(docx_path)
        style_result = surgeon.surgical_style_edit(xpath_expr, properties)

        if not style_result.get("success", False) or style_result.get("nodes_modified", 0) == 0:
            return json.dumps({
                "success": False,
                "reason": "No se aplicaron cambios.",
                "detail": style_result,
            }, ensure_ascii=False, indent=2)

        commit_result = surgeon.commit_changes(output_path)

        return json.dumps({
            "success": True,
            "style_edit": style_result,
            "commit": commit_result,
        }, ensure_ascii=False, indent=2)

    except Exception as exc:
        log.error("[TOOL ERROR] surgical_style_edit: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 8: inspect_images
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def inspect_images(
    docx_path: Annotated[str, "Ruta al .docx a operar"],
) -> str:
    """
    Escanea el documento y extrae todas las imágenes referenciadas en el XML.
    Útil para encontrar el rId y el nombre físico de una imagen antes de reemplazarla.
    """
    log.info("[TOOL] inspect_images")
    try:
        surgeon = DocxSurgeon(docx_path)
        images = surgeon.inspect_images()
        return json.dumps({
            "success": True,
            "total_images": len(images),
            "images": images
        }, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] inspect_images: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)

# ─────────────────────────────────────────────────────────────────────────────
# TOOL 9: surgical_replace_image  (Opción A)
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def surgical_replace_image(
    docx_path: Annotated[str, "Ruta al .docx a operar"],
    r_id: Annotated[str | None, "El Relationship ID (ej. 'rId5') de la imagen a reemplazar. Puede ser None si se usa zip_target"],
    new_image_path: Annotated[str, "Ruta a la nueva imagen local"],
    zip_target: Annotated[str | None, "Ruta directa en el ZIP (ej. 'word/media/image3.jpeg') si no se conoce el r_id. Útil para imágenes en headers."] = None,
    output_path: Annotated[str | None, "Ruta de salida. Si es None sobreescribe el original"] = None,
) -> str:
    """Reemplaza físicamente una imagen dentro del paquete DOCX."""
    log.info("[TOOL] surgical_replace_image: %s / %s con %s", r_id, zip_target, new_image_path)
    try:
        surgeon = DocxSurgeon(docx_path)
        replace_result = surgeon.surgical_replace_image(r_id, new_image_path, zip_target=zip_target)
        
        if not replace_result.get("success", False):
            return json.dumps(replace_result, ensure_ascii=False, indent=2)
            
        commit_result = surgeon.commit_changes(output_path)
        return json.dumps({
            "success": True,
            "replace": replace_result,
            "commit": commit_result,
        }, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] surgical_replace_image: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)

# ─────────────────────────────────────────────────────────────────────────────
# TOOL 10: surgical_inject_image  (Opción B)
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def surgical_inject_image(
    docx_path: Annotated[str, "Ruta al .docx a operar"],
    xpath_expr: Annotated[str, "XPath exacto del párrafo (w:p) donde inyectar la imagen"],
    new_image_path: Annotated[str, "Ruta a la nueva imagen local"],
    width_inches: Annotated[float | None, "Ancho deseado en pulgadas (opcional, preserva proporción)"] = None,
    height_inches: Annotated[float | None, "Alto deseado en pulgadas (opcional, preserva proporción)"] = None,
    output_path: Annotated[str | None, "Ruta de salida. Si es None sobreescribe el original"] = None,
) -> str:
    """Inyecta una imagen completamente nueva en el párrafo especificado con preservación de proporciones."""
    log.info("[TOOL] surgical_inject_image: %s en %s", new_image_path, xpath_expr)
    try:
        surgeon = DocxSurgeon(docx_path)
        inject_result = surgeon.surgical_inject_image(
            xpath_expr=xpath_expr,
            new_image_path=new_image_path,
            width_inches=width_inches,
            height_inches=height_inches,
        )
        
        if not inject_result.get("success", False):
            return json.dumps(inject_result, ensure_ascii=False, indent=2)
            
        commit_result = surgeon.commit_changes(output_path)
        return json.dumps({
            "success": True,
            "inject": inject_result,
            "commit": commit_result,
        }, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] surgical_inject_image: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 11: inject_toc  (Tabla de Contenido Automática)
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def inject_toc(
    docx_path: Annotated[str, "Ruta al .docx donde insertar la tabla de contenido"],
    anchor_text: Annotated[str, "Texto del párrafo ancla (ej. 'INDICE' o 'Tabla de Contenido')"],
    heading_range: Annotated[str, "Rango de headings a incluir, formato 'min-max' (ej. '1-3')"] = "1-3",
    title: Annotated[str, "Título visible sobre la tabla de contenido (vacío = sin título)"] = "",
    position: Annotated[str, "'before', 'after' o 'replace'"] = "replace",
    output_path: Annotated[str | None, "Ruta de salida. Si es None sobreescribe el original"] = None,
) -> str:
    """
    Inyecta una Tabla de Contenido (TOC) nativa de Word en el documento.

    Genera un campo TOC OOXML completo con:
    - \\o "1-3" → niveles de heading a incluir
    - \\h → hipervínculos internos
    - \\z → ocultar números de página en vista web
    - \\u → usar estilos de outline

    La TOC se actualiza automáticamente al abrir el documento en Word
    (Word mostrará un aviso para actualizar los campos).

    Parámetros:
    - anchor_text: texto del párrafo que servirá de ancla (ej. 'INDICE')
    - heading_range: '1-3' incluye Heading 1, 2 y 3
    - position: 'replace' sustituye el párrafo ancla por la TOC
    """
    log.info("[TOOL] inject_toc: anchor=%r, range=%s, position=%s",
             anchor_text, heading_range, position)
    try:
        from copy import deepcopy

        from lxml import etree as _etree

        surgeon = DocxSurgeon(docx_path)
        body = surgeon.tree.find(qn("w", "body"))
        if body is None:
            return json.dumps({"error": "No se encontró <w:body>"}, ensure_ascii=False)

        # Localizar el párrafo ancla
        anchor_para = None
        anchor_idx = -1
        for idx, child in enumerate(body):
            if child.tag != qn("w", "p"):
                continue
            para_text = "".join(
                (t.text or "") for t in child.iter(qn("w", "t"))
            )
            if anchor_text in para_text:
                anchor_para = child
                anchor_idx = idx
                break

        if anchor_para is None:
            return json.dumps({
                "success": False,
                "error": f"No se encontró párrafo con texto: {anchor_text!r}"
            }, ensure_ascii=False, indent=2)

        # Construir los nodos de la TOC
        toc_nodes = []

        # 1. Título opcional
        if title:
            title_xml = f'''
            <w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                <w:pPr>
                    <w:jc w:val="center"/>
                </w:pPr>
                <w:r>
                    <w:rPr>
                        <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"
                                  w:cs="Times New Roman" w:eastAsia="Times New Roman"/>
                        <w:b/>
                        <w:sz w:val="28"/>
                        <w:szCs w:val="28"/>
                    </w:rPr>
                    <w:t>{title}</w:t>
                </w:r>
            </w:p>'''
            toc_nodes.append(_etree.fromstring(title_xml.strip()))

        # 2. SDT con el campo TOC
        sdt_xml = f'''
        <w:sdt xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
            <w:sdtPr>
                <w:docPartObj>
                    <w:docPartGallery w:val="Table of Contents"/>
                    <w:docPartUnique/>
                </w:docPartObj>
            </w:sdtPr>
            <w:sdtContent>
                <w:p>
                    <w:r>
                        <w:fldChar w:fldCharType="begin"/>
                    </w:r>
                    <w:r>
                        <w:instrText xml:space="preserve"> TOC \\o "{heading_range}" \\h \\z \\u </w:instrText>
                    </w:r>
                    <w:r>
                        <w:fldChar w:fldCharType="separate"/>
                    </w:r>
                    <w:r>
                        <w:rPr>
                            <w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>
                            <w:sz w:val="24"/>
                        </w:rPr>
                        <w:t>Actualice este campo para ver la tabla de contenido (Ctrl+A, F9)</w:t>
                    </w:r>
                    <w:r>
                        <w:fldChar w:fldCharType="end"/>
                    </w:r>
                </w:p>
            </w:sdtContent>
        </w:sdt>'''
        toc_nodes.append(_etree.fromstring(sdt_xml.strip()))

        # 3. Inyectar en la posición correcta
        if position == "replace":
            body.remove(anchor_para)
            for offset, node in enumerate(toc_nodes):
                body.insert(anchor_idx + offset, deepcopy(node))
        elif position == "after":
            for offset, node in enumerate(toc_nodes):
                body.insert(anchor_idx + 1 + offset, deepcopy(node))
        elif position == "before":
            for offset, node in enumerate(toc_nodes):
                body.insert(anchor_idx + offset, deepcopy(node))

        # 4. Marcar updateFields en settings.xml para auto-actualizar la TOC
        surgeon._dirty = True

        # 5. Commit
        commit_result = surgeon.commit_changes(output_path)

        return json.dumps({
            "success": True,
            "toc_heading_range": heading_range,
            "title": title or "(sin título)",
            "position": position,
            "anchor_index": anchor_idx,
            "commit": commit_result,
            "note": "Al abrir en Word, haga clic derecho sobre la TOC → 'Actualizar campo' para poblar las entradas."
        }, ensure_ascii=False, indent=2)

    except Exception as exc:
        log.error("[TOOL ERROR] inject_toc: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


import json

from src.mcp_documents.core.executor import ToolExecutor

lucero_executor = ToolExecutor()

# ─────────────────────────────────────────────────────────────────────────────
# LUCERO PRO STACK TOOLS (Universal Bridge)
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def pro_read_document(
    file_path: Annotated[str, "Path to document file (DOCX, PDF, MD, TXT)"],
    extract_type: Annotated[str, "Extraction type: full_text, metadata, tables, all"] = "full_text"
) -> str:
    """Read any document and extract its content."""
    res = await lucero_executor.execute("mcp", "read_document", {"file_path": file_path, "extract_type": extract_type})
    return json.dumps(res, ensure_ascii=False, indent=2)

@mcp.tool()
async def pro_write_document(
    file_path: Annotated[str, "Path to save document"],
    content: Annotated[str, "Content to write (Markdown syntax supported for DOCX)"],
    format: Annotated[str, "Format: docx, md, txt"] = "docx",
    append: Annotated[bool, "Append to existing file"] = False,
    encrypt: Annotated[bool, "Encrypt output using AES-256"] = False,
    password: Annotated[str, "Password for encryption (if encrypt is True)"] = ""
) -> str:
    """Write or modify documents with full formatting support."""
    params = {
        "file_path": file_path, 
        "content": content, 
        "format": format, 
        "append": append, 
        "encrypt": encrypt, 
        "password": password
    }
    res = await lucero_executor.execute("mcp", "write_document", params)
    return json.dumps(res, ensure_ascii=False, indent=2)

@mcp.tool()
async def pro_transform_document(
    source_path: Annotated[str, "Path to source document"],
    target_format: Annotated[str, "Target format: pdf, docx, md"]
) -> str:
    """Convert between document formats (e.g., DOCX to PDF, DOCX to MD)."""
    res = await lucero_executor.execute("mcp", "transform_document", {"source_path": source_path, "target_format": target_format})
    return json.dumps(res, ensure_ascii=False, indent=2)

@mcp.tool()
async def pro_encrypt_document(
    file_path: Annotated[str, "Path to the file to encrypt"],
    password: Annotated[str, "Password for AES-256 encryption"],
    output_path: Annotated[str | None, "Optional custom output path"] = None
) -> str:
    """Encrypt documents with AES-256 and PBKDF2."""
    res = await lucero_executor.execute("mcp", "encrypt_document", {"file_path": file_path, "password": password, "output_path": output_path})
    return json.dumps(res, ensure_ascii=False, indent=2)

# ─────────────────────────────────────────────────────────────────────────────
# HERRAMIENTAS DE NIVEL ÉLITE (TIERS 1-5)
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def compare_documents(
    ctx: Context,
    document_paths: Annotated[list[str], "Lista de rutas absolutas de los archivos a comparar (PDF, DOCX, TXT, MD)"],
) -> str:
    """
    Compara de forma inteligente múltiples documentos de gestión pública para identificar
    puntos en común, contradicciones explícitas y vacíos de información (gaps).
    """
    from src.herramientas_elite import comparar_documentos_impl
    log.info("[TOOL] compare_documents: %d archivos", len(document_paths))
    try:
        res = await comparar_documentos_impl(document_paths, ctx=ctx)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] compare_documents: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
async def extract_selective(
    ctx: Context,
    document_path: Annotated[str, "Ruta absoluta al archivo a analizar (PDF, DOCX, TXT, MD)"],
    extract_type: Annotated[str, "Tipo de información a extraer: 'dates', 'tables', 'metadata', 'names' u otra específica"],
) -> str:
    """
    Extrae selectivamente del documento la información solicitada sin devolver todo el texto completo.
    Especialmente útil para aislar fechas, tablas o nombres de personas/organizaciones de forma limpia.
    """
    from src.herramientas_elite import extraer_selectivo_impl
    log.info("[TOOL] extract_selective: %s (%s)", document_path, extract_type)
    try:
        res = await extraer_selectivo_impl(document_path, extract_type, ctx=ctx)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] extract_selective: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
async def detect_conflicts(
    ctx: Context,
    document_paths: Annotated[list[str], "Lista de rutas absolutas a los archivos a analizar de forma cruzada"],
) -> str:
    """
    Detecta discrepancias, inconsistencias conceptuales o discrepancias de datos (ej. montos discrepantes o
    fechas contradictorias para un mismo suceso) entre múltiples documentos.
    """
    from src.herramientas_elite import detectar_conflictos_impl
    log.info("[TOOL] detect_conflicts: %d archivos", len(document_paths))
    try:
        res = await detectar_conflictos_impl(document_paths, ctx=ctx)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] detect_conflicts: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
async def generate_summary(
    ctx: Context,
    document_path: Annotated[str, "Ruta absoluta al documento a resumir"],
    summary_type: Annotated[str, "Tipo de resumen: 'executive' (resumen ejecutivo), 'detailed' (analítico) o 'bullets' (viñetas)"] = "executive",
) -> str:
    """
    Genera un resumen inteligente y adaptado al tipo solicitado en español para un documento largo.
    """
    from src.herramientas_elite import generar_resumen_impl
    log.info("[TOOL] generate_summary: %s (%s)", document_path, summary_type)
    try:
        res = await generar_resumen_impl(document_path, summary_type, ctx=ctx)
        return json.dumps({"resumen": res}, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] generate_summary: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
async def create_checklist(
    ctx: Context,
    document_path: Annotated[str, "Ruta absoluta al documento que contiene los lineamientos o directivas"],
) -> str:
    """
    Analiza un documento de directrices, requerimientos o contrato y genera una lista de verificación (checklist)
    de tareas e hitos estructurada en JSON.
    """
    from src.herramientas_elite import crear_checklist_impl
    log.info("[TOOL] create_checklist: %s", document_path)
    try:
        res = await crear_checklist_impl(document_path, ctx=ctx)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] create_checklist: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
async def extract_timeline(
    ctx: Context,
    document_path: Annotated[str, "Ruta absoluta al documento"],
) -> str:
    """
    Extrae todos los eventos con fecha de un documento de forma estructurada y los ordena cronológicamente.
    """
    from src.herramientas_elite import extraer_cronograma_impl
    log.info("[TOOL] extract_timeline: %s", document_path)
    try:
        res = await extraer_cronograma_impl(document_path, ctx=ctx)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] extract_timeline: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
async def generate_rubric(
    ctx: Context,
    document_path: Annotated[str, "Ruta al documento de evaluación o guías"],
) -> str:
    """
    Crea una tabla estructurada de rúbrica de evaluación con criterios, niveles de desempeño
    y ponderaciones basados en el texto provisto.
    """
    from src.herramientas_elite import generar_rubrica_impl
    log.info("[TOOL] generate_rubric: %s", document_path)
    try:
        res = await generar_rubrica_impl(document_path, ctx=ctx)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] generate_rubric: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
async def smart_merge(
    ctx: Context,
    document_paths: Annotated[list[str], "Lista de rutas de documentos a fusionar"],
) -> str:
    """
    Fusiona el contenido e información clave de múltiples documentos relacionados eliminando duplicidades
    y redactando un texto maestro consolidado en formato Markdown.
    """
    from src.herramientas_elite import fusion_inteligente_impl
    log.info("[TOOL] smart_merge: %d archivos", len(document_paths))
    try:
        res = await fusion_inteligente_impl(document_paths, ctx=ctx)
        return json.dumps({"merged_content": res}, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] smart_merge: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
async def validate_structure(
    ctx: Context,
    document_path: Annotated[str, "Ruta al documento a validar"],
) -> str:
    """
    Valida la estructura formal del documento, reportando errores estructurales graves,
    advertencias menores y otorgando una calificación general del diseño del contenido de 0 a 100.
    """
    from src.herramientas_elite import validar_estructura_impl
    log.info("[TOOL] validate_structure: %s", document_path)
    try:
        res = await validar_estructura_impl(document_path, ctx=ctx)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] validate_structure: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
async def ocr_quality_score(
    ctx: Context,
    document_path: Annotated[str, "Ruta al documento digitalizado o con OCR"],
) -> str:
    """
    Evalúa la calidad del texto extraído en busca de artefactos de OCR corruptos,
    caracteres extraños o errores tipográficos sistemáticos del escaneo.
    """
    from src.herramientas_elite import calidad_ocr_impl
    log.info("[TOOL] ocr_quality_score: %s", document_path)
    try:
        res = await calidad_ocr_impl(document_path, ctx=ctx)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] ocr_quality_score: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
async def cross_reference(
    ctx: Context,
    document_paths: Annotated[list[str], "Lista de rutas de los documentos a mapear"],
) -> str:
    """
    Mapea referencias y relaciones implícitas o explícitas entre un conjunto de documentos.
    Identifica de qué forma se mencionan, citan o contradicen.
    """
    from src.herramientas_elite import mapa_referencias_impl
    log.info("[TOOL] cross_reference: %d archivos", len(document_paths))
    try:
        res = await mapa_referencias_impl(document_paths, ctx=ctx)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] cross_reference: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
async def completeness_check(
    ctx: Context,
    document_path: Annotated[str, "Ruta al documento a auditar"],
    expected_sections: Annotated[list[str], "Lista de secciones obligatorias a buscar (ej: ['Antecedentes', 'Presupuesto'])"],
) -> str:
    """
    Analiza si el documento contiene un listado específico de secciones requeridas,
    indicando cuáles faltan y cómo completarlas.
    """
    from src.herramientas_elite import verificacion_completitud_impl
    log.info("[TOOL] completeness_check: %s", document_path)
    try:
        res = await verificacion_completitud_impl(document_path, expected_sections, ctx=ctx)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] completeness_check: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
async def batch_process(
    ctx: Context,
    folder_path: Annotated[str, "Ruta absoluta a la carpeta con documentos"],
    action: Annotated[str, "Operación a realizar: 'resumen', 'cronograma' o 'calidad'"],
    extension_filter: Annotated[str, "Filtro de extensión (ej. '.pdf', '.docx' o '*')"] = "*",
) -> str:
    """
    Procesa por lotes todos los documentos de una carpeta aplicando una acción específica
    y devolviendo un reporte consolidado.
    """
    from src.herramientas_elite import procesar_lote_impl
    log.info("[TOOL] batch_process: %s (%s)", folder_path, action)
    try:
        res = await procesar_lote_impl(folder_path, action, extension_filter, ctx=ctx)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] batch_process: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
async def version_tracking(
    ctx: Context,
    document_path_1: Annotated[str, "Ruta al documento de la versión anterior"],
    document_path_2: Annotated[str, "Ruta al documento de la versión actual"],
) -> str:
    """
    Identifica de forma conceptual los cambios, adiciones, eliminaciones o reformulaciones
    entre dos versiones del mismo archivo.
    """
    from src.herramientas_elite import seguimiento_versiones_impl
    log.info("[TOOL] version_tracking: %s vs %s", document_path_1, document_path_2)
    try:
        res = await seguimiento_versiones_impl(document_path_1, document_path_2, ctx=ctx)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] version_tracking: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
async def create_index(
    ctx: Context,
    document_path: Annotated[str, "Ruta al documento"],
) -> str:
    """
    Genera un índice temático y conceptual estructurado de temas clave discutidos en el documento.
    """
    from src.herramientas_elite import crear_indice_impl
    log.info("[TOOL] create_index: %s", document_path)
    try:
        res = await crear_indice_impl(document_path, ctx=ctx)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] create_index: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
async def extract_relationships(
    ctx: Context,
    document_paths: Annotated[list[str], "Lista de rutas de documentos"],
) -> str:
    """
    Extrae un grafo relacional de personas, organizaciones, fechas, leyes y conceptos clave
    entrelazados en la documentación.
    """
    from src.herramientas_elite import extraer_relaciones_impl
    log.info("[TOOL] extract_relationships: %d archivos", len(document_paths))
    try:
        res = await extraer_relaciones_impl(document_paths, ctx=ctx)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] extract_relationships: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
async def generate_qa_pairs(
    ctx: Context,
    document_path: Annotated[str, "Ruta al documento"],
) -> str:
    """
    Genera de forma automática pares estructurados de Preguntas y Respuestas esperadas sobre el
    contenido del documento para facilitar entrenamiento o autoevaluación.
    """
    from src.herramientas_elite import generar_preguntas_respuestas_impl
    log.info("[TOOL] generate_qa_pairs: %s", document_path)
    try:
        res = await generar_preguntas_respuestas_impl(document_path, ctx=ctx)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] generate_qa_pairs: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
async def create_executive_brief(
    ctx: Context,
    document_paths: Annotated[list[str], "Lista de rutas de expedientes o documentos"],
) -> str:
    """
    Consolida un informe ejecutivo analítico ultra-condensado de 1 página a partir de múltiples
    documentos o carpetas complejas.
    """
    from src.herramientas_elite import briefing_ejecutivo_impl
    log.info("[TOOL] create_executive_brief: %d archivos", len(document_paths))
    try:
        res = await briefing_ejecutivo_impl(document_paths, ctx=ctx)
        return json.dumps({"briefing": res}, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] create_executive_brief: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
async def generate_action_items(
    ctx: Context,
    document_path: Annotated[str, "Ruta al documento"],
) -> str:
    """
    Extrae tareas accionables detalladas del documento con responsables implícitos y plazos inferidos.
    """
    from src.herramientas_elite import generar_items_accion_impl
    log.info("[TOOL] generate_action_items: %s", document_path)
    try:
        res = await generar_items_accion_impl(document_path)
        return json.dumps(res, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] generate_action_items: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRYPOINT
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# TIER 1/2 EXCEL: CIRUGIA Y MANIPULACION QUIRURGICA DE HOJAS DE CALCULO
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def inspect_excel_sheets(
    excel_path: Annotated[str, "Ruta absoluta o relativa al archivo Excel (.xlsx / .xlsm) a inspeccionar"],
) -> str:
    """
    Inspecciona la totalidad de hojas de un libro Excel:
    nombre, visibilidad, dimensiones (ej. 'A1:F40'), total de filas y columnas con datos,
    tablas estructuradas y rangos de celdas combinadas.
    """
    log.info("[TOOL] inspect_excel_sheets: %s", excel_path)
    try:
        from src.xlsx_surgeon import XlsxSurgeon
        with XlsxSurgeon(excel_path, solo_lectura=False) as cirujano:
            hojas = cirujano.inspeccionar_hojas()
            return json.dumps({
                "archivo": Path(excel_path).name,
                "total_hojas": len(hojas),
                "hojas": hojas,
            }, ensure_ascii=False)
    except Exception as exc:
        log.error("[TOOL ERROR] inspect_excel_sheets: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
def inspect_excel_cells(
    excel_path: Annotated[str, "Ruta absoluta o relativa al archivo Excel (.xlsx / .xlsm)"],
    sheet_name: Annotated[str | None, "Nombre de la hoja a inspeccionar. Si es None, usa la hoja activa"] = None,
    cell_range: Annotated[str | None, "Rango de celdas especifico (ej. 'A1:D20' o 'B5'). Si es None, analiza las filas activas"] = None,
    max_rows: Annotated[int, "Limite maximo de filas a inspeccionar (default 100)"] = 100,
) -> str:
    """
    Inspecciona en profundidad un rango de celdas o filas de una hoja de calculo:
    extrae valores, formulas, tipos de datos (texto, numero, fecha, etc.) y metadatos
    de estilo (fuente, negrita, tamano, color, alineacion, relleno y formato numerico).
    """
    log.info("[TOOL] inspect_excel_cells: %s (hoja: %s, rango: %s, max_filas: %d)",
             excel_path, sheet_name, cell_range, max_rows)
    try:
        from src.xlsx_surgeon import XlsxSurgeon
        with XlsxSurgeon(excel_path, solo_lectura=False) as cirujano:
            resultado = cirujano.inspeccionar_celdas(
                nombre_hoja=sheet_name,
                rango_celdas=cell_range,
                max_filas=max_rows,
            )
            return json.dumps(resultado, ensure_ascii=False)
    except Exception as exc:
        log.error("[TOOL ERROR] inspect_excel_cells: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
def surgical_replace_excel_cell(
    excel_path: Annotated[str, "Ruta absoluta o relativa al archivo Excel"],
    coordinate: Annotated[str, "Coordenada de la celda a modificar (ej. 'B4' o 'F12')"],
    new_value: Annotated[str, "Nuevo valor a inyectar (texto, numero o formula que inicie con '=')"],
    sheet_name: Annotated[str | None, "Nombre de la hoja. Si es None, utiliza la hoja activa"] = None,
    is_formula: Annotated[bool, "Indica explicitamente si el valor debe tratarse como formula"] = False,
    output_path: Annotated[str | None, "Ruta de salida. Si es None, sobreescribe el archivo original"] = None,
) -> str:
    """
    Modifica atomicamente una celda en una hoja de Excel garantizando el principio
    de ZERO FORMAT LOSS: preserva intactas la fuente, bordes, rellenos, alineacion
    y formato numerico original de la celda.
    """
    log.info("[TOOL] surgical_replace_excel_cell: %s [%s!%s] -> '%s'",
             excel_path, sheet_name or "activa", coordinate, new_value)
    try:
        from src.xlsx_surgeon import XlsxSurgeon
        with XlsxSurgeon(excel_path) as cirujano:
            hoja_real = sheet_name or cirujano.libro.active.title
            informe = cirujano.reemplazar_celda_quirurgica(
                nombre_hoja=hoja_real,
                coordenada=coordinate,
                nuevo_valor=new_value,
                es_formula=is_formula,
            )
            ruta_salida = cirujano.guardar(output_path)
            informe["archivo_guardado"] = str(ruta_salida)
            return json.dumps(informe, ensure_ascii=False)
    except Exception as exc:
        log.error("[TOOL ERROR] surgical_replace_excel_cell: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
def surgical_inject_excel_table(
    excel_path: Annotated[str, "Ruta absoluta o relativa al archivo Excel"],
    start_cell: Annotated[str, "Celda inicial superior izquierda donde comenzara la tabla (ej. 'A1' o 'C5')"],
    headers: Annotated[list[str], "Lista de nombres de encabezados de columna"],
    rows: Annotated[list[list[Any]], "Matriz de datos con las filas a inyectar"],
    sheet_name: Annotated[str | None, "Nombre de la hoja. Si es None, utiliza la hoja activa"] = None,
    table_name: Annotated[str | None, "Nombre formal de la tabla estructurada Excel (opcional)"] = None,
    apply_aurora_style: Annotated[bool, "Si True, aplica tipografia Space Grotesk/Inter y diseno sobrio"] = False,
    output_path: Annotated[str | None, "Ruta de salida. Si es None, sobreescribe el archivo original"] = None,
) -> str:
    """
    Inyecta una tabla o conjunto de datos estructurados en una hoja de calculo,
    con autoajuste inteligente de anchos de columna y opcion de aplicar el sistema
    de estilo sobrio del Aldraverso.
    """
    log.info("[TOOL] surgical_inject_excel_table: %s [%s!%s] (%d cols, %d filas)",
             excel_path, sheet_name or "activa", start_cell, len(headers), len(rows))
    try:
        from src.xlsx_surgeon import XlsxSurgeon
        with XlsxSurgeon(excel_path) as cirujano:
            hoja_real = sheet_name or cirujano.libro.active.title
            informe = cirujano.inyectar_tabla_quirurgica(
                nombre_hoja=hoja_real,
                celda_inicio=start_cell,
                encabezados=headers,
                filas=rows,
                nombre_tabla=table_name,
                aplicar_estilo_aurora=apply_aurora_style,
            )
            ruta_salida = cirujano.guardar(output_path)
            informe["archivo_guardado"] = str(ruta_salida)
            return json.dumps(informe, ensure_ascii=False)
    except Exception as exc:
        log.error("[TOOL ERROR] surgical_inject_excel_table: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


@mcp.tool()
def surgical_search_replace_excel(
    excel_path: Annotated[str, "Ruta absoluta o relativa al archivo Excel"],
    search_text: Annotated[str, "Texto que se desea buscar en las celdas"],
    replace_text: Annotated[str, "Texto por el cual se reemplazara"],
    sheet_name: Annotated[str | None, "Nombre de hoja especifica o None para buscar en todo el libro"] = None,
    exact_match: Annotated[bool, "Si True, solo sustituye si la celda coincide exactamente con el texto"] = False,
    output_path: Annotated[str | None, "Ruta de salida. Si es None, sobreescribe el archivo original"] = None,
) -> str:
    """
    Busca y reemplaza cadenas de texto en las celdas de una o todas las hojas del libro,
    conservando intactas las formulas, fuentes, colores, bordes y formatos numericos.
    """
    log.info("[TOOL] surgical_search_replace_excel: %s buscando '%s' -> '%s'",
             excel_path, search_text, replace_text)
    try:
        from src.xlsx_surgeon import XlsxSurgeon
        with XlsxSurgeon(excel_path) as cirujano:
            informe = cirujano.buscar_y_reemplazar(
                texto_buscar=search_text,
                texto_reemplazo=replace_text,
                nombre_hoja=sheet_name,
                coincidencia_exacta=exact_match,
            )
            ruta_salida = cirujano.guardar(output_path)
            informe["archivo_guardado"] = str(ruta_salida)
            return json.dumps(informe, ensure_ascii=False)
    except Exception as exc:
        log.error("[TOOL ERROR] surgical_search_replace_excel: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
    except Exception as exc:
        log.error("[TOOL ERROR] surgical_search_replace_excel: %s", exc, exc_info=True)
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


def run() -> None:
    log.info("Iniciando LUCERO (Décimo Hermano) MCP Server...")
    mcp.run()

if __name__ == "__main__":
    run()
