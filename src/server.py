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

from mcp.server.fastmcp import FastMCP, Context

from .apa_templates import (
    TEMPLATE_CATALOG,
    apa_body_paragraph,
    apa_figure_label,
    apa_figure_note,
    apa_heading1,
    apa_heading2,
    apa_heading3,
    apa_in_text_citation,
    apa_reference_entry,
)
from .surgeon import DocxSurgeon
from .pptx_surgeon import PptxSurgeon
from .excel_surgeon import ExcelSurgeon
from .optimizador_tokens import (
    generar_diff_compacto,
    paginar_lista,
    serializar_respuesta_compacta,
    serializar_toon,
)
from .navegador_documentos import (
    buscar_en_documento,
    leer_rango_documento,
    obtener_esquema_documento,
)
from .utils import JsonDict, get_logger

log = get_logger("lucero.server")

# ─────────────────────────────────────────────────────────────────────────────
# INSTANCIA MCP
# ─────────────────────────────────────────────────────────────────────────────
mcp = FastMCP(
    name="LUCERO",
    instructions=(
        "Servidor MCP de manipulacion quirurgica de documentos .docx y presentaciones .pptx (PPT-Master).\n"
        "Opera directamente sobre el XML interno (ECMA-376) y DrawingML con precision de nodo y zero format loss.\n\n"
        "Capacidades integradas:\n"
        "1. DOCX (LUCERO Core): inspect_xml_tree, surgical_replace, inject_apa_structure, commit_changes\n"
        "2. PPTX (PPT-Master Hermano): pptx_inspect_slides, pptx_surgical_replace, pptx_inject_image, "
        "pptx_compile_from_svg, pptx_render_latex, pptx_to_markdown, pptx_to_svg\n"
    ),
)

# ─────────────────────────────────────────────────────────────────────────────
# TOOL 1: inspect_xml_tree
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def inspect_xml_tree(
    docx_path: Annotated[str, "Ruta absoluta al archivo .docx"],
    max_paragraphs: Annotated[int, "Maximo de parrafos a devolver (default 100)"] = 100,
    style_filter: Annotated[str | None, "Filtrar por ID de estilo (ej. 'Heading1')"] = None,
    offset: Annotated[int, "Indice de parrafo inicial para paginacion (default 0)"] = 0,
    lightweight: Annotated[bool, "Si es True, omite runs y XPath para ahorrar tokens"] = False,
) -> str:
    """Devuelve mapa estructural del .docx (paraId, estilo, texto y opcionalmente runs/XPath)."""
    log.info("[TOOL] inspect_xml_tree: %s (max=%d, offset=%d, filter=%s, light=%s)",
             docx_path, max_paragraphs, offset, style_filter, lightweight)
    try:
        surgeon = DocxSurgeon(docx_path)
        data = surgeon.inspect_tree(max_paragraphs=offset + max_paragraphs)

        if style_filter:
            data = [p for p in data if p.get("style") == style_filter]

        paginado = paginar_lista(data, inicio=offset, limite=max_paragraphs)
        parrafos_salida = paginado["elementos"]
        if lightweight:
            parrafos_salida = [
                {
                    "index": p.get("index"),
                    "paraId": p.get("paraId"),
                    "style": p.get("style"),
                    "text": p.get("text"),
                }
                for p in parrafos_salida
            ]

        styles = surgeon.get_styles_list()
        result = {
            "file": Path(docx_path).name,
            "total_paragraphs_scanned": paginado["mostrados"],
            "offset": offset,
            "hay_mas": paginado["hay_mas"],
            "siguiente_offset": paginado.get("siguiente_inicio"),
            "styles_used": styles,
            "paragraphs": parrafos_salida,
        }
        return serializar_toon(
            result,
            nota_paginacion=f"Usa offset={offset + max_paragraphs} o lightweight=True en inspect_xml_tree.",
        )

    except Exception as exc:
        log.error("[TOOL ERROR] inspect_xml_tree: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 2: surgical_replace
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def surgical_replace(
    docx_path: Annotated[str, "Ruta al .docx a operar"],
    target_text: Annotated[str, "Texto exacto a localizar en nodos <w:t>"],
    replacement_text: Annotated[str, "Texto de reemplazo (preserva formato)"],
    output_path: Annotated[str | None, "Ruta de salida; None sobrescribe original"] = None,
    occurrence: Annotated[int, "Aparicion a reemplazar: 1=primera, -1=todas"] = 1,
) -> str:
    """Reemplaza texto en nodos <w:t> preservando el formato <w:rPr> y hace commit automatico."""
    log.info("[TOOL] surgical_replace: %r -> %r en %s",
             target_text, replacement_text, docx_path)
    try:
        surgeon = DocxSurgeon(docx_path)
        replace_result = surgeon.surgical_replace(
            target_text=target_text,
            replacement_text=replacement_text,
            occurrence=occurrence,
        )

        if replace_result["occurrences_replaced"] == 0:
            return serializar_respuesta_compacta({
                "success": False,
                "reason": f"No se encontro '{target_text}' en el documento.",
                "detail": replace_result,
            })

        commit_result = surgeon.commit_changes(output_path)
        diff_compacto = generar_diff_compacto(
            target_text,
            replacement_text,
            etiqueta=Path(docx_path).name,
        )

        return serializar_respuesta_compacta({
            "success": True,
            "replace": replace_result,
            "commit": commit_result,
            "diff": diff_compacto,
        })

    except Exception as exc:
        log.error("[TOOL ERROR] surgical_replace: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


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
            return serializar_respuesta_compacta(inject_result)

        commit_result = surgeon.commit_changes(output_path)

        return json.dumps({
            "success":  True,
            "template": template_type,
            "inject":   inject_result,
            "commit":   commit_result,
        }, ensure_ascii=False, indent=2)

    except Exception as exc:
        log.error("[TOOL ERROR] inject_apa_structure: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


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
        return serializar_respuesta_compacta(result)
    except Exception as exc:
        log.error("[TOOL ERROR] commit_changes: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 4.1: insertar_parrafo_clonado
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def insertar_parrafo_clonado(
    docx_path: Annotated[str, "Ruta al .docx objetivo"],
    texto_ancla: Annotated[str, "Texto del párrafo ancla del cual clonar el formato"],
    segmentos: Annotated[list[str], "Textos de los runs del nuevo párrafo"],
    posicion: Annotated[str, "'antes' o 'despues'"] = "despues",
    aparicion: Annotated[int, "Qué aparición del párrafo ancla usar (1-based)"] = 1,
    output_path: Annotated[str | None, "Ruta de salida (None = sobreescribir)"] = None,
) -> str:
    """
    Crea un nuevo párrafo clonando exactamente las propiedades (pPr: viñeta, sangría,
    estilo) del párrafo ancla, asignando a cada segmento el formato (rPr) de los runs
    del ancla. Garantiza que párrafos insertados tengan exactamente la misma estética.
    """
    log.info("[TOOL] insertar_parrafo_clonado en %s (ancla=%r, pos=%s)", docx_path, texto_ancla, posicion)
    try:
        surgeon = DocxSurgeon(docx_path)
        inject_res = surgeon.insertar_parrafo_clonado(
            texto_ancla=texto_ancla,
            segmentos=segmentos,
            posicion=posicion,
            aparicion=aparicion,
        )
        if not inject_res.get("success"):
            return serializar_respuesta_compacta(inject_res)

        commit_res = surgeon.commit_changes(output_path)
        return json.dumps({
            "success": True,
            "inject": inject_res,
            "commit": commit_res,
        }, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] insertar_parrafo_clonado: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 4.2: lote_quirurgico
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def lote_quirurgico(
    docx_path: Annotated[str, "Ruta al .docx objetivo"],
    operaciones: Annotated[list[dict[str, Any]], (
        "Lista de operaciones ordenadas:\n"
        "- {'tipo': 'reemplazar', 'objetivo': str, 'reemplazo': str, 'aparicion': int, 'esperadas': int}\n"
        "- {'tipo': 'insertar', 'ancla': str, 'segmentos': list[str], 'posicion': 'despues'|'antes', 'aparicion': int}"
    )],
    output_path: Annotated[str | None, "Ruta de salida (None = sobreescribir)"] = None,
    simulacion: Annotated[bool, "Si True, ejecuta en memoria y retorna el plan sin escribir a disco"] = False,
) -> str:
    """
    Ejecuta un conjunto atómico de reemplazos e inserciones en memoria.
    Si cualquier operación falla (p. ej. texto no encontrado o apariciones esperadas no coinciden),
    se cancela todo y NO se toca el archivo.
    Si todas triunfan y simulacion=False, realiza un único commit con respaldo automático.
    """
    log.info("[TOOL] lote_quirurgico en %s (%d operaciones, simulacion=%s)",
             docx_path, len(operaciones), simulacion)
    try:
        surgeon = DocxSurgeon(docx_path)
        resultado_lote = surgeon.aplicar_lote(operaciones)
        if not resultado_lote.get("exito"):
            return json.dumps({
                "success": False,
                "reason": f"El lote falló en la operación #{resultado_lote.get('fallo_en')}",
                "detail": resultado_lote,
            }, ensure_ascii=False, indent=2)

        if simulacion:
            return json.dumps({
                "success": True,
                "simulacion": True,
                "operaciones_ejecutadas": len(operaciones),
                "detail": resultado_lote,
            }, ensure_ascii=False, indent=2)

        commit_res = surgeon.commit_changes(output_path)
        return json.dumps({
            "success": True,
            "simulacion": False,
            "operaciones_ejecutadas": len(operaciones),
            "detail": resultado_lote,
            "commit": commit_res,
        }, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] lote_quirurgico: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 4.3: ensamblar_documento_maestro
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def ensamblar_documento_maestro(
    docx_plantilla: Annotated[str, "Ruta al .docx plantilla maestro (ej. Indice LTHDA)"],
    docx_hoja_presentacion: Annotated[str, "Ruta al .docx con la hoja membretada oficial"],
    docx_contenido_cuerpo: Annotated[str, "Ruta al .docx con el cuerpo desarrollado"],
    output_path: Annotated[str | None, "Ruta de salida (None = sobreescribir la plantilla)"] = None,
    limite_portada_parrafos: Annotated[int, "Máximo de párrafos de portada a extraer"] = 30,
    ancla_indice: Annotated[str, "Texto que identifica el inicio del índice"] = "Índice",
    ancla_cuerpo: Annotated[str, "Texto que identifica el inicio del cuerpo"] = "Resumen",
    identificador_cuerpo: Annotated[str, "Palabra clave para desambiguar el cuerpo real"] = "EmpleaTEC",
) -> str:
    """
    Ensambla quirúrgicamente una plantilla maestra con portada institucional y cuerpo completo:
    - Extrae la portada oficial y transplanta los logos a word/media remapeando sus relaciones rId.
    - Preserva intacto el Índice oficial de la plantilla docente.
    - Sustituye las instrucciones de la plantilla por el contenido desarrollado formal en APA 7
      (Times New Roman 12, justificado, 1.5 interlineado y sangría francesa en bibliografía).
    - Ejecuta un commit seguro con respaldo automático timestamped.
    """
    log.info("[TOOL] ensamblar_documento_maestro en %s", docx_plantilla)
    try:
        surgeon = DocxSurgeon(docx_plantilla)
        res_ensamblado = surgeon.ensamblar_plantilla_maestra(
            ruta_hoja_presentacion=docx_hoja_presentacion,
            ruta_contenido_cuerpo=docx_contenido_cuerpo,
            limite_portada_parrafos=limite_portada_parrafos,
            ancla_indice=ancla_indice,
            ancla_cuerpo_destino=ancla_cuerpo,
            ancla_cuerpo_origen=ancla_cuerpo,
            identificador_cuerpo_origen=identificador_cuerpo,
        )
        if not res_ensamblado.get("success"):
            return serializar_respuesta_compacta(res_ensamblado)

        commit_res = surgeon.commit_changes(output_path)
        return json.dumps({
            "success": True,
            "ensamblado": res_ensamblado,
            "commit": commit_res,
        }, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] ensamblar_documento_maestro: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 4.4: exportar_a_markdown
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def exportar_a_markdown(
    docx_path: Annotated[str, "Ruta al archivo .docx a convertir en Markdown"],
    output_path: Annotated[str | None, "Ruta de salida para el archivo .md (None = mismo nombre .md)"] = None,
) -> str:
    """
    Convierte un documento .docx a formato Markdown usando el motor MarkItDown,
    preservando encabezados, tablas, listas y enlaces sin modificar ni borrar el DOCX original.
    """
    log.info("[TOOL] exportar_a_markdown en %s -> %s", docx_path, output_path)
    try:
        surgeon = DocxSurgeon(docx_path)
        res = surgeon.exportar_a_markdown(output_path)
        return serializar_respuesta_compacta(res)
    except Exception as exc:
        log.error("[TOOL ERROR] exportar_a_markdown: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


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
    return serializar_respuesta_compacta(catalog_out)


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

        return serializar_toon({
            "xpath":        xpath_expr,
            "total_found":  len(nodes),
            "shown":        len(results),
            "results":      results,
        })

    except Exception as exc:
        log.error("[TOOL ERROR] run_xpath: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


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
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
def edit_section_layout(
    file_path: Annotated[str, "Ruta al .docx"],
    margins_twips: Annotated[dict[str, int] | None, "Margenes {top, bottom, left, right} en twips"] = None,
    page_size_twips: Annotated[dict[str, int] | None, "Tamano {w, h} en twips"] = None,
    enforce_apa_page_number: Annotated[bool, "Inyecta numeracion APA en esquina superior derecha"] = False,
) -> str:
    """Ajusta margenes, tamano de hoja y numeracion APA en secciones (//w:sectPr) y encabezados."""
    log.info("[TOOL] edit_section_layout: %s", file_path)
    try:
        surgeon = DocxSurgeon(file_path)
        res = surgeon.edit_section_layout(
            margins_twips=margins_twips,
            page_size_twips=page_size_twips,
            enforce_apa_page_number=enforce_apa_page_number,
        )
        if res["secciones_modificadas"] > 0 or res["encabezados_modificados"] > 0:
            surgeon.commit_changes()
        return (
            f"OK: {res['secciones_modificadas']} secciones y "
            f"{res['encabezados_modificados']} encabezados actualizados"
        )
    except Exception as exc:
        log.error("[TOOL ERROR] edit_section_layout: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
def batch_normalize_styles(
    file_path: Annotated[str, "Ruta al .docx"],
    target_xpath: Annotated[str | None, "XPath de nodos w:p o w:r en document.xml"] = None,
    update_doc_defaults: Annotated[bool, "Actualiza docDefaults y Normal en word/styles.xml"] = False,
    set_font: Annotated[str | None, "Fuente (ej. 'Times New Roman')"] = None,
    set_size_half_pts: Annotated[int | None, "Tamano en medios puntos (ej. 24 = 12pt)"] = None,
    set_align: Annotated[str | None, "Alineacion: left, center, right, both"] = None,
    set_line_spacing: Annotated[int | None, "Interlineado en 240avos (ej. 480 = doble)"] = None,
    set_space_after: Annotated[int | None, "Espacio posterior en twips (ej. 0)"] = None,
) -> str:
    """Normaliza estilos globales en styles.xml y/o nodos XPath en document.xml en una llamada."""
    log.info("[TOOL] batch_normalize_styles: %s", file_path)
    try:
        surgeon = DocxSurgeon(file_path)
        res = surgeon.batch_normalize_styles(
            target_xpath=target_xpath,
            update_doc_defaults=update_doc_defaults,
            set_font=set_font,
            set_size_half_pts=set_size_half_pts,
            set_align=set_align,
            set_line_spacing=set_line_spacing,
            set_space_after=set_space_after,
        )
        if res["nodos_actualizados"] > 0:
            surgeon.commit_changes()
        return f"OK: {res['nodos_actualizados']} nodos actualizados"
    except Exception as exc:
        log.error("[TOOL ERROR] batch_normalize_styles: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


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
        return serializar_respuesta_compacta({"error": str(exc)})

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
            return serializar_respuesta_compacta(replace_result)
            
        commit_result = surgeon.commit_changes(output_path)
        return json.dumps({
            "success": True,
            "replace": replace_result,
            "commit": commit_result,
        }, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] surgical_replace_image: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})

# ─────────────────────────────────────────────────────────────────────────────
# TOOL 10: surgical_inject_image  (Opción B)
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def surgical_inject_image(
    docx_path: Annotated[str, "Ruta al .docx a operar"],
    xpath_expr: Annotated[str, "XPath exacto del párrafo (w:p) donde inyectar la imagen"],
    new_image_path: Annotated[str, "Ruta a la nueva imagen local"],
    output_path: Annotated[str | None, "Ruta de salida. Si es None sobreescribe el original"] = None,
) -> str:
    """Inyecta una imagen completamente nueva en el párrafo especificado."""
    log.info("[TOOL] surgical_inject_image: %s en %s", new_image_path, xpath_expr)
    try:
        surgeon = DocxSurgeon(docx_path)
        inject_result = surgeon.surgical_inject_image(xpath_expr, new_image_path)
        
        if not inject_result.get("success", False):
            return serializar_respuesta_compacta(inject_result)
            
        commit_result = surgeon.commit_changes(output_path)
        return json.dumps({
            "success": True,
            "inject": inject_result,
            "commit": commit_result,
        }, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] surgical_inject_image: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


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
        from lxml import etree as _etree
        from copy import deepcopy

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
        return serializar_respuesta_compacta({"error": str(exc)})


from .mcp_documents.core.executor import ToolExecutor
import json

lucero_executor = ToolExecutor()

# ─────────────────────────────────────────────────────────────────────────────
# LUCERO PRO STACK TOOLS (Universal Bridge)
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
async def pro_read_document(
    file_path: Annotated[str, "Ruta al documento (DOCX, PDF, PPTX, TXT)"],
    extract_type: Annotated[str, "Tipo: full_text, metadata, tables, all"] = "full_text",
    start_line: Annotated[int | None, "Linea inicial base 1 (opcional)"] = None,
    end_line: Annotated[int | None, "Linea final inclusiva (opcional)"] = None,
    search_query: Annotated[str | None, "Texto a buscar con contexto acotado (opcional)"] = None,
    outline_only: Annotated[bool, "Si es True, devuelve solo indice estructural ligero"] = False,
    offset: Annotated[int, "Desplazamiento inicial en caracteres para paginacion"] = 0,
    limit: Annotated[int, "Maximo de caracteres por pagina (default 8000)"] = 8000,
) -> str:
    """Lee un documento completo, por rango de lineas numeradas, por busqueda acotada o solo su indice."""
    res = await lucero_executor.execute(
        "mcp",
        "read_document",
        {
            "file_path": file_path,
            "extract_type": extract_type,
            "start_line": start_line,
            "end_line": end_line,
            "search_query": search_query,
            "outline_only": outline_only,
            "offset": offset,
            "limit": limit,
        },
    )
    return serializar_respuesta_compacta(
        res,
        limite=max(500, limit),
        nota_paginacion=f"Usa offset={offset + limit} o start_line/end_line en pro_read_document.",
    )


@mcp.tool()
def get_document_outline(
    file_path: Annotated[str, "Ruta absoluta al archivo (DOCX, PPTX, XLSX, PDF, TXT)"],
    max_items: Annotated[int, "Maximo de elementos estructurales a devolver"] = 100,
) -> str:
    """Devuelve un indice ligero (encabezados, diapositivas, hojas o paginas) con su linea o indice."""
    try:
        esquema = obtener_esquema_documento(file_path, max_elementos=max_items)
        return serializar_toon(esquema)
    except Exception as exc:
        log.error("[TOOL ERROR] get_document_outline: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
def search_in_doc(
    file_path: Annotated[str, "Ruta absoluta al archivo (DOCX, PPTX, XLSX, PDF, TXT)"],
    query: Annotated[str, "Texto a buscar dentro del documento"],
    context_lines: Annotated[int, "Lineas de margen superior e inferior por coincidencia"] = 2,
    max_matches: Annotated[int, "Maximo de coincidencias a devolver"] = 20,
) -> str:
    """Busca texto en un documento y devuelve coincidencias numeradas con contexto acotado."""
    try:
        res = buscar_en_documento(
            file_path,
            consulta=query,
            lineas_contexto=context_lines,
            max_coincidencias=max_matches,
        )
        return serializar_respuesta_compacta(res)
    except Exception as exc:
        log.error("[TOOL ERROR] search_in_doc: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})

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
    return serializar_respuesta_compacta(res)

@mcp.tool()
async def pro_transform_document(
    source_path: Annotated[str, "Path to source document"],
    target_format: Annotated[str, "Target format: pdf, docx, md"],
    output_path: Annotated[str | None, "Optional custom output path"] = None
) -> str:
    """Convert between document formats (e.g., DOCX to PDF, DOCX to MD) using Microsoft MarkItDown for MD."""
    res = await lucero_executor.execute("mcp", "transform_document", {
        "source_path": source_path,
        "target_format": target_format,
        "output_path": output_path
    })
    return serializar_respuesta_compacta(res)

@mcp.tool()
async def pro_encrypt_document(
    file_path: Annotated[str, "Path to the file to encrypt"],
    password: Annotated[str, "Password for AES-256 encryption"],
    output_path: Annotated[str | None, "Optional custom output path"] = None
) -> str:
    """Encrypt documents with AES-256 and PBKDF2."""
    res = await lucero_executor.execute("mcp", "encrypt_document", {"file_path": file_path, "password": password, "output_path": output_path})
    return serializar_respuesta_compacta(res)

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
    from .herramientas_elite import comparar_documentos_impl
    log.info("[TOOL] compare_documents: %d archivos", len(document_paths))
    try:
        res = await comparar_documentos_impl(document_paths, ctx=ctx)
        return serializar_respuesta_compacta(res)
    except Exception as exc:
        log.error("[TOOL ERROR] compare_documents: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


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
    from .herramientas_elite import extraer_selectivo_impl
    log.info("[TOOL] extract_selective: %s (%s)", document_path, extract_type)
    try:
        res = await extraer_selectivo_impl(document_path, extract_type, ctx=ctx)
        return serializar_respuesta_compacta(res)
    except Exception as exc:
        log.error("[TOOL ERROR] extract_selective: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
async def detect_conflicts(
    ctx: Context,
    document_paths: Annotated[list[str], "Lista de rutas absolutas a los archivos a analizar de forma cruzada"],
) -> str:
    """
    Detecta discrepancias, inconsistencias conceptuales o discrepancias de datos (ej. montos discrepantes o
    fechas contradictorias para un mismo suceso) entre múltiples documentos.
    """
    from .herramientas_elite import detectar_conflictos_impl
    log.info("[TOOL] detect_conflicts: %d archivos", len(document_paths))
    try:
        res = await detectar_conflictos_impl(document_paths, ctx=ctx)
        return serializar_respuesta_compacta(res)
    except Exception as exc:
        log.error("[TOOL ERROR] detect_conflicts: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
async def generate_summary(
    ctx: Context,
    document_path: Annotated[str, "Ruta absoluta al documento a resumir"],
    summary_type: Annotated[str, "Tipo de resumen: 'executive' (resumen ejecutivo), 'detailed' (analítico) o 'bullets' (viñetas)"] = "executive",
) -> str:
    """
    Genera un resumen inteligente y adaptado al tipo solicitado en español para un documento largo.
    """
    from .herramientas_elite import generar_resumen_impl
    log.info("[TOOL] generate_summary: %s (%s)", document_path, summary_type)
    try:
        res = await generar_resumen_impl(document_path, summary_type, ctx=ctx)
        return serializar_respuesta_compacta({"resumen": res})
    except Exception as exc:
        log.error("[TOOL ERROR] generate_summary: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
async def create_checklist(
    ctx: Context,
    document_path: Annotated[str, "Ruta absoluta al documento que contiene los lineamientos o directivas"],
) -> str:
    """
    Analiza un documento de directrices, requerimientos o contrato y genera una lista de verificación (checklist)
    de tareas e hitos estructurada en JSON.
    """
    from .herramientas_elite import crear_checklist_impl
    log.info("[TOOL] create_checklist: %s", document_path)
    try:
        res = await crear_checklist_impl(document_path, ctx=ctx)
        return serializar_respuesta_compacta(res)
    except Exception as exc:
        log.error("[TOOL ERROR] create_checklist: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
async def extract_timeline(
    ctx: Context,
    document_path: Annotated[str, "Ruta absoluta al documento"],
) -> str:
    """
    Extrae todos los eventos con fecha de un documento de forma estructurada y los ordena cronológicamente.
    """
    from .herramientas_elite import extraer_cronograma_impl
    log.info("[TOOL] extract_timeline: %s", document_path)
    try:
        res = await extraer_cronograma_impl(document_path, ctx=ctx)
        return serializar_respuesta_compacta(res)
    except Exception as exc:
        log.error("[TOOL ERROR] extract_timeline: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
async def generate_rubric(
    ctx: Context,
    document_path: Annotated[str, "Ruta al documento de evaluación o guías"],
) -> str:
    """
    Crea una tabla estructurada de rúbrica de evaluación con criterios, niveles de desempeño
    y ponderaciones basados en el texto provisto.
    """
    from .herramientas_elite import generar_rubrica_impl
    log.info("[TOOL] generate_rubric: %s", document_path)
    try:
        res = await generar_rubrica_impl(document_path, ctx=ctx)
        return serializar_respuesta_compacta(res)
    except Exception as exc:
        log.error("[TOOL ERROR] generate_rubric: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
async def smart_merge(
    ctx: Context,
    document_paths: Annotated[list[str], "Lista de rutas de documentos a fusionar"],
) -> str:
    """
    Fusiona el contenido e información clave de múltiples documentos relacionados eliminando duplicidades
    y redactando un texto maestro consolidado en formato Markdown.
    """
    from .herramientas_elite import fusion_inteligente_impl
    log.info("[TOOL] smart_merge: %d archivos", len(document_paths))
    try:
        res = await fusion_inteligente_impl(document_paths, ctx=ctx)
        return serializar_respuesta_compacta({"merged_content": res})
    except Exception as exc:
        log.error("[TOOL ERROR] smart_merge: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
async def validate_structure(
    ctx: Context,
    document_path: Annotated[str, "Ruta al documento a validar"],
) -> str:
    """
    Valida la estructura formal del documento, reportando errores estructurales graves,
    advertencias menores y otorgando una calificación general del diseño del contenido de 0 a 100.
    """
    from .herramientas_elite import validar_estructura_impl
    log.info("[TOOL] validate_structure: %s", document_path)
    try:
        res = await validar_estructura_impl(document_path, ctx=ctx)
        return serializar_respuesta_compacta(res)
    except Exception as exc:
        log.error("[TOOL ERROR] validate_structure: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
async def ocr_quality_score(
    ctx: Context,
    document_path: Annotated[str, "Ruta al documento digitalizado o con OCR"],
) -> str:
    """
    Evalúa la calidad del texto extraído en busca de artefactos de OCR corruptos,
    caracteres extraños o errores tipográficos sistemáticos del escaneo.
    """
    from .herramientas_elite import calidad_ocr_impl
    log.info("[TOOL] ocr_quality_score: %s", document_path)
    try:
        res = await calidad_ocr_impl(document_path, ctx=ctx)
        return serializar_respuesta_compacta(res)
    except Exception as exc:
        log.error("[TOOL ERROR] ocr_quality_score: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
async def cross_reference(
    ctx: Context,
    document_paths: Annotated[list[str], "Lista de rutas de los documentos a mapear"],
) -> str:
    """
    Mapea referencias y relaciones implícitas o explícitas entre un conjunto de documentos.
    Identifica de qué forma se mencionan, citan o contradicen.
    """
    from .herramientas_elite import mapa_referencias_impl
    log.info("[TOOL] cross_reference: %d archivos", len(document_paths))
    try:
        res = await mapa_referencias_impl(document_paths, ctx=ctx)
        return serializar_respuesta_compacta(res)
    except Exception as exc:
        log.error("[TOOL ERROR] cross_reference: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


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
    from .herramientas_elite import verificacion_completitud_impl
    log.info("[TOOL] completeness_check: %s", document_path)
    try:
        res = await verificacion_completitud_impl(document_path, expected_sections, ctx=ctx)
        return serializar_respuesta_compacta(res)
    except Exception as exc:
        log.error("[TOOL ERROR] completeness_check: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


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
    from .herramientas_elite import procesar_lote_impl
    log.info("[TOOL] batch_process: %s (%s)", folder_path, action)
    try:
        res = await procesar_lote_impl(folder_path, action, extension_filter, ctx=ctx)
        return serializar_respuesta_compacta(res)
    except Exception as exc:
        log.error("[TOOL ERROR] batch_process: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


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
    from .herramientas_elite import seguimiento_versiones_impl
    log.info("[TOOL] version_tracking: %s vs %s", document_path_1, document_path_2)
    try:
        res = await seguimiento_versiones_impl(document_path_1, document_path_2, ctx=ctx)
        return serializar_respuesta_compacta(res)
    except Exception as exc:
        log.error("[TOOL ERROR] version_tracking: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
async def create_index(
    ctx: Context,
    document_path: Annotated[str, "Ruta al documento"],
) -> str:
    """
    Genera un índice temático y conceptual estructurado de temas clave discutidos en el documento.
    """
    from .herramientas_elite import crear_indice_impl
    log.info("[TOOL] create_index: %s", document_path)
    try:
        res = await crear_indice_impl(document_path, ctx=ctx)
        return serializar_respuesta_compacta(res)
    except Exception as exc:
        log.error("[TOOL ERROR] create_index: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
async def extract_relationships(
    ctx: Context,
    document_paths: Annotated[list[str], "Lista de rutas de documentos"],
) -> str:
    """
    Extrae un grafo relacional de personas, organizaciones, fechas, leyes y conceptos clave
    entrelazados en la documentación.
    """
    from .herramientas_elite import extraer_relaciones_impl
    log.info("[TOOL] extract_relationships: %d archivos", len(document_paths))
    try:
        res = await extraer_relaciones_impl(document_paths, ctx=ctx)
        return serializar_respuesta_compacta(res)
    except Exception as exc:
        log.error("[TOOL ERROR] extract_relationships: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
async def generate_qa_pairs(
    ctx: Context,
    document_path: Annotated[str, "Ruta al documento"],
) -> str:
    """
    Genera de forma automática pares estructurados de Preguntas y Respuestas esperadas sobre el
    contenido del documento para facilitar entrenamiento o autoevaluación.
    """
    from .herramientas_elite import generar_preguntas_respuestas_impl
    log.info("[TOOL] generate_qa_pairs: %s", document_path)
    try:
        res = await generar_preguntas_respuestas_impl(document_path, ctx=ctx)
        return serializar_respuesta_compacta(res)
    except Exception as exc:
        log.error("[TOOL ERROR] generate_qa_pairs: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
async def create_executive_brief(
    ctx: Context,
    document_paths: Annotated[list[str], "Lista de rutas de expedientes o documentos"],
) -> str:
    """
    Consolida un informe ejecutivo analítico ultra-condensado de 1 página a partir de múltiples
    documentos o carpetas complejas.
    """
    from .herramientas_elite import briefing_ejecutivo_impl
    log.info("[TOOL] create_executive_brief: %d archivos", len(document_paths))
    try:
        res = await briefing_ejecutivo_impl(document_paths, ctx=ctx)
        return serializar_respuesta_compacta({"briefing": res})
    except Exception as exc:
        log.error("[TOOL ERROR] create_executive_brief: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
async def generate_action_items(
    ctx: Context,
    document_path: Annotated[str, "Ruta al documento"],
) -> str:
    """
    Extrae tareas accionables detalladas del documento con responsables implícitos y plazos inferidos.
    """
    from .herramientas_elite import generar_items_accion_impl
    log.info("[TOOL] generate_action_items: %s", document_path)
    try:
        res = await generar_items_accion_impl(document_path, ctx=ctx)
        return serializar_respuesta_compacta(res)
    except Exception as exc:
        log.error("[TOOL ERROR] generate_action_items: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


# ─────────────────────────────────────────────────────────────────────────────
# HERRAMIENTAS PPT-MASTER (HERMANO NATIVO DE PRESENTACIONES)
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool()
def pptx_inspect_slides(
    pptx_path: Annotated[str, "Ruta absoluta al archivo .pptx a inspeccionar"],
    offset: Annotated[int, "Indice de diapositiva inicial (base 0) para paginacion"] = 0,
    limit: Annotated[int, "Maximo de diapositivas a devolver por llamada"] = 20,
) -> str:
    """Inspecciona diapositivas de un .pptx devolviendo formas, tablas, notas y coordenadas en cm."""
    log.info("[TOOL] pptx_inspect_slides: %s (offset=%d, limit=%d)", pptx_path, offset, limit)
    try:
        cirujano = PptxSurgeon(pptx_path)
        diapositivas = cirujano.inspeccionar_diapositivas()
        paginado = paginar_lista(diapositivas, inicio=offset, limite=limit)
        resultado = {
            "archivo": Path(pptx_path).name,
            "total_diapositivas": paginado["total"],
            "offset": offset,
            "hay_mas": paginado["hay_mas"],
            "siguiente_offset": paginado.get("siguiente_inicio"),
            "diapositivas": paginado["elementos"],
        }
        return serializar_toon(
            resultado,
            nota_paginacion=f"Usa offset={offset + limit} en pptx_inspect_slides para ver mas diapositivas.",
        )
    except Exception as exc:
        log.error("[TOOL ERROR] pptx_inspect_slides: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
def pptx_surgical_replace(
    pptx_path: Annotated[str, "Ruta al archivo .pptx"],
    search_text: Annotated[str, "Texto exacto a buscar en formas o celdas de tabla"],
    replace_text: Annotated[str, "Nuevo texto que reemplazara al objetivo"],
    output_path: Annotated[str | None, "Ruta de salida opcional. Si se omite, sobrescribe el archivo"] = None,
) -> str:
    """Reemplaza texto en formas o tablas de un .pptx preservando el formato de runs."""
    log.info("[TOOL] pptx_surgical_replace: %s ('%s' -> '%s')", pptx_path, search_text, replace_text)
    try:
        cirujano = PptxSurgeon(pptx_path)
        total = cirujano.reemplazo_quirurgico_texto(
            texto_buscar=search_text,
            texto_reemplazo=replace_text,
            ruta_salida=output_path
        )
        diff_compacto = generar_diff_compacto(
            search_text,
            replace_text,
            etiqueta=Path(pptx_path).name,
        ) if total > 0 else ""
        return serializar_respuesta_compacta({
            "exito": total > 0,
            "reemplazos_realizados": total,
            "archivo_salida": output_path or pptx_path,
            "diff": diff_compacto,
        })
    except Exception as exc:
        log.error("[TOOL ERROR] pptx_surgical_replace: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
def pptx_inject_image(
    pptx_path: Annotated[str, "Ruta al archivo .pptx"],
    slide_index: Annotated[int, "Indice de la diapositiva (base 1)"],
    image_path: Annotated[str, "Ruta absoluta de la imagen a insertar"],
    left_cm: Annotated[float, "Posicion horizontal en centimetros desde el borde izquierdo"],
    top_cm: Annotated[float, "Posicion vertical en centimetros desde el borde superior"],
    width_cm: Annotated[float | None, "Ancho en centimetros (opcional)"] = None,
    height_cm: Annotated[float | None, "Alto en centimetros (opcional)"] = None,
    output_path: Annotated[str | None, "Ruta de salida opcional"] = None,
) -> str:
    """
    Inyecta una imagen o grafica con coordenadas metricas exactas en una diapositiva especifica.
    """
    log.info("[TOOL] pptx_inject_image: %s (slide=%d, img=%s)", pptx_path, slide_index, image_path)
    try:
        cirujano = PptxSurgeon(pptx_path)
        exito = cirujano.inyectar_imagen_diapositiva(
            indice_diapositiva=slide_index,
            ruta_imagen=image_path,
            izquierda_cm=left_cm,
            arriba_cm=top_cm,
            ancho_cm=width_cm,
            alto_cm=height_cm,
            ruta_salida=output_path
        )
        return json.dumps({
            "exito": exito,
            "diapositiva": slide_index,
            "archivo_salida": output_path or pptx_path
        }, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] pptx_inject_image: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
def pptx_render_latex(
    formula_latex: Annotated[str, "Expresion matematica en sintaxis LaTeX"],
    output_png: Annotated[str, "Ruta del archivo PNG resultante"],
    dpi: Annotated[int, "Resolucion en puntos por pulgada (default 300)"] = 300,
    color_hex: Annotated[str, "Color hexadecimal de la fuente (default '000000')"] = "000000",
    background_hex: Annotated[str, "Color hexadecimal de fondo (default 'FFFFFF')"] = "FFFFFF",
    transparent: Annotated[bool, "Si es True, aplica transparencia alfa al fondo"] = True,
) -> str:
    """
    Renderiza una ecuacion matematica en sintaxis LaTeX a una imagen PNG de alta definicion (300 DPI)
    con fondo transparente mediante la cadena de proveedores de PPT-Master (CodeCogs, QuickLaTeX, MathPad).
    """
    log.info("[TOOL] pptx_render_latex: %s -> %s", formula_latex, output_png)
    try:
        resultado = PptxSurgeon.renderizar_formula_latex(
            formula_latex=formula_latex,
            ruta_salida_png=output_png,
            dpi=dpi,
            color_hex=color_hex,
            fondo_hex=background_hex,
            hacer_transparente=transparent
        )
        return serializar_respuesta_compacta(resultado)
    except Exception as exc:
        log.error("[TOOL ERROR] pptx_render_latex: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
def pptx_compile_from_svg(
    svg_paths: Annotated[list[str], "Lista de rutas de diapositivas en formato SVG"],
    output_pptx: Annotated[str, "Ruta de la presentacion .pptx a generar"],
    canvas_format: Annotated[str, "Formato de lienzo (default 'ppt169')"] = "ppt169",
    native_shapes: Annotated[bool, "Si es True, genera formas DrawingML editables nativas"] = True,
    transition: Annotated[str, "Efecto de transicion de diapositiva (default 'fade')"] = "fade",
) -> str:
    """
    Compila un conjunto de diapositivas disenadas en SVG a una presentacion PowerPoint editable
    utilizando el compilador DrawingML de PPT-Master, garantizando nitidez vectorial a cualquier escala.
    """
    log.info("[TOOL] pptx_compile_from_svg: %d diapositivas -> %s", len(svg_paths), output_pptx)
    try:
        exito = PptxSurgeon.compilar_desde_svg(
            archivos_svg=svg_paths,
            ruta_salida_pptx=output_pptx,
            formato_lienzo=canvas_format,
            formas_nativas=native_shapes,
            transicion=transition
        )
        return json.dumps({
            "exito": exito,
            "archivo_salida": output_pptx,
            "total_diapositivas": len(svg_paths)
        }, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] pptx_compile_from_svg: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
def pptx_to_markdown(
    pptx_path: Annotated[str, "Ruta al archivo .pptx"],
    output_md: Annotated[str | None, "Ruta opcional para guardar el Markdown"] = None,
) -> str:
    """
    Extrae el contenido completo de una presentacion PPTX a Markdown estructurado,
    incluyendo titulos, texto por diapositiva, tablas y notas del orador.
    """
    log.info("[TOOL] pptx_to_markdown: %s", pptx_path)
    try:
        md = PptxSurgeon.extraer_a_markdown(pptx_path, ruta_salida_md=output_md)
        return json.dumps({
            "exito": True,
            "archivo": pptx_path,
            "archivo_salida": output_md,
            "longitud_caracteres": len(md),
            "markdown": md
        }, ensure_ascii=False, indent=2)
    except Exception as exc:
        log.error("[TOOL ERROR] pptx_to_markdown: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
def pptx_to_svg(
    pptx_path: Annotated[str, "Ruta al archivo .pptx"],
    output_dir: Annotated[str, "Carpeta donde se guardaran los archivos SVG de cada diapositiva"],
) -> str:
    """
    Convierte una presentacion PPTX en una coleccion de archivos SVG individuales
    leyendo directamente el arbol OOXML sin requerir PowerPoint instalado.
    """
    log.info("[TOOL] pptx_to_svg: %s -> %s", pptx_path, output_dir)
    try:
        res = PptxSurgeon.convertir_a_svg(pptx_path, output_dir)
        return serializar_respuesta_compacta(res)
    except Exception as exc:
        log.error("[TOOL ERROR] pptx_to_svg: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
def inspect_excel_sheets(
    excel_path: Annotated[str, "Ruta absoluta al archivo .xlsx"],
) -> str:
    """
    Inspecciona la totalidad de hojas de un libro Excel:
    nombre, visibilidad, dimensiones, total de filas y columnas con datos, tablas y celdas combinadas.
    """
    log.info("[TOOL] inspect_excel_sheets: %s", excel_path)
    try:
        res = ExcelSurgeon.inspect_sheets(excel_path)
        return serializar_toon(res)
    except Exception as exc:
        log.error("[TOOL ERROR] inspect_excel_sheets: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
def inspect_excel_cells(
    excel_path: Annotated[str, "Ruta absoluta al archivo .xlsx"],
    sheet_name: Annotated[str | None, "Nombre de la hoja a inspeccionar (opcional, por defecto activa)"] = None,
    cell_range: Annotated[str | None, "Rango de celdas matricial (ej. 'A1:M60', opcional)"] = None,
    max_rows: Annotated[int, "Numero maximo de filas a retornar"] = 100,
) -> str:
    """
    Inspecciona en profundidad un rango de celdas o filas de una hoja de calculo:
    extrae valores, formulas, tipos de datos y metadatos de estilo.
    """
    log.info("[TOOL] inspect_excel_cells: %s (hoja=%s, rango=%s)", excel_path, sheet_name, cell_range)
    try:
        res = ExcelSurgeon.inspect_cells(excel_path, sheet_name, cell_range, max_rows)
        return serializar_toon(res)
    except Exception as exc:
        log.error("[TOOL ERROR] inspect_excel_cells: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
def surgical_replace_excel_cell(
    excel_path: Annotated[str, "Ruta absoluta al archivo .xlsx"],
    coordinate: Annotated[str, "Coordenada de la celda a reemplazar (ej. 'C14')"],
    new_value: Annotated[str, "Nuevo valor a asignar"],
    sheet_name: Annotated[str | None, "Nombre de la hoja (opcional, por defecto activa)"] = None,
    is_formula: Annotated[bool, "Si es True, el nuevo valor se trata como formula matematica"] = False,
    output_path: Annotated[str | None, "Ruta de salida (opcional, por defecto sobrescribe in-place)"] = None,
) -> str:
    """
    Modifica atomicamente una celda en una hoja de Excel garantizando el principio
    de ZERO FORMAT LOSS: preserva intactas la fuente, bordes, rellenos y alineacion original.
    """
    log.info("[TOOL] surgical_replace_excel_cell: %s en %s -> %s", excel_path, coordinate, new_value)
    try:
        res = ExcelSurgeon.surgical_replace_cell(excel_path, coordinate, new_value, sheet_name, is_formula, output_path)
        return serializar_respuesta_compacta(res)
    except Exception as exc:
        log.error("[TOOL ERROR] surgical_replace_excel_cell: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
def surgical_inject_excel_table(
    excel_path: Annotated[str, "Ruta absoluta al archivo .xlsx"],
    start_cell: Annotated[str, "Coordenada superior izquierda donde iniciara la tabla (ej. 'A1')"],
    headers: Annotated[list[str], "Lista de encabezados de la tabla"],
    rows: Annotated[list[list[Any]], "Matriz de datos con las filas a inyectar"],
    sheet_name: Annotated[str | None, "Nombre de la hoja (opcional, por defecto activa)"] = None,
    table_name: Annotated[str | None, "Nombre descriptivo de la tabla (opcional)"] = None,
    apply_aurora_style: Annotated[bool, "Si es True, aplica paleta de estilos sobrios del Aldraverso"] = False,
    output_path: Annotated[str | None, "Ruta de salida (opcional, por defecto sobrescribe in-place)"] = None,
) -> str:
    """
    Inyecta una tabla o conjunto de datos estructurados en una hoja de calculo,
    con autoajuste inteligente de anchos de columna y preservacion de formulas.
    """
    log.info("[TOOL] surgical_inject_excel_table: %s en %s (%d filas)", excel_path, start_cell, len(rows))
    try:
        res = ExcelSurgeon.surgical_inject_table(
            excel_path, start_cell, headers, rows, sheet_name, table_name, apply_aurora_style, output_path
        )
        return serializar_respuesta_compacta(res)
    except Exception as exc:
        log.error("[TOOL ERROR] surgical_inject_excel_table: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


@mcp.tool()
def surgical_search_replace_excel(
    excel_path: Annotated[str, "Ruta absoluta al archivo .xlsx"],
    search_text: Annotated[str, "Texto o cadena a buscar"],
    replace_text: Annotated[str, "Texto de reemplazo"],
    sheet_name: Annotated[str | None, "Nombre de la hoja especifica (None = todas las hojas)"] = None,
    exact_match: Annotated[bool, "Si es True, la celda debe coincidir exactamente con search_text"] = False,
    output_path: Annotated[str | None, "Ruta de salida (opcional, por defecto sobrescribe in-place)"] = None,
) -> str:
    """
    Busca y reemplaza cadenas de texto en las celdas de una o todas las hojas del libro,
    conservando intactas las formulas, fuentes, colores, bordes y formatos numericos.
    """
    log.info("[TOOL] surgical_search_replace_excel: %s ('%s' -> '%s')", excel_path, search_text, replace_text)
    try:
        res = ExcelSurgeon.surgical_search_replace(
            excel_path, search_text, replace_text, sheet_name, exact_match, output_path
        )
        return serializar_respuesta_compacta(res)
    except Exception as exc:
        log.error("[TOOL ERROR] surgical_search_replace_excel: %s", exc, exc_info=True)
        return serializar_respuesta_compacta({"error": str(exc)})


# ─────────────────────────────────────────────────────────────────────────────
# ENTRYPOINT
# ─────────────────────────────────────────────────────────────────────────────

def run() -> None:
    log.info("Iniciando LUCERO (Decimo Hermano) MCP Server...")
    mcp.run()

if __name__ == "__main__":
    run()
