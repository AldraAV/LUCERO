"""
navegador_documentos.py — Exploracion ligera (outline), lectura por rangos con
numeracion de lineas y busqueda acotada estilo grep para DOCX, PPTX, XLSX, PDF y TXT.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from docx import Document
from pypdf import PdfReader

from .optimizador_tokens import (
    buscar_con_contexto,
    extraer_rango_lineas,
)

FORMATOS_SOPORTADOS = {".docx", ".pptx", ".xlsx", ".xlsm", ".pdf", ".txt"}


def _validar_ruta(ruta_archivo: str) -> Path:
    if not ruta_archivo or not str(ruta_archivo).strip():
        raise ValueError("La ruta del archivo no puede estar vacia.")
    ruta = Path(ruta_archivo)
    if not ruta.exists():
        raise FileNotFoundError(f"El archivo no existe: {ruta}")
    if ruta.suffix.lower() not in FORMATOS_SOPORTADOS:
        raise ValueError(
            f"Formato no soportado '{ruta.suffix}'. Soportados: {sorted(FORMATOS_SOPORTADOS)}"
        )
    return ruta


def extraer_texto_plano_documento(ruta: Path) -> str:
    """
    Extrae texto plano limpio por lineas de DOCX, PPTX, XLSX, PDF o TXT.
    """
    sufijo = ruta.suffix.lower()

    if sufijo == ".txt":
        return ruta.read_text(encoding="utf-8", errors="replace")

    if sufijo == ".docx":
        doc = Document(str(ruta))
        lineas = [p.text for p in doc.paragraphs]
        for idx_t, tabla in enumerate(doc.tables, start=1):
            lineas.append(f"[Tabla {idx_t}]")
            for fila in tabla.rows:
                lineas.append(" | ".join(c.text.strip() for c in fila.cells))
        return "\n".join(lineas)

    if sufijo == ".pdf":
        lector = PdfReader(str(ruta))
        bloques: list[str] = []
        for idx, pagina in enumerate(lector.pages, start=1):
            texto_pag = (pagina.extract_text() or "").strip()
            bloques.append(f"--- Pagina {idx} ---")
            if texto_pag:
                bloques.append(texto_pag)
        return "\n".join(bloques)

    if sufijo == ".pptx":
        from .pptx_surgeon import PptxSurgeon

        cirujano = PptxSurgeon(str(ruta))
        diapositivas = cirujano.inspeccionar_diapositivas()
        lineas_pptx: list[str] = []
        for diap in diapositivas:
            lineas_pptx.append(f"--- Diapositiva {diap['indice']} ---")
            for forma in diap.get("formas", []):
                texto = (forma.get("texto_completo") or "").strip()
                if texto:
                    lineas_pptx.append(f"[{forma.get('nombre', 'Forma')}] {texto}")
                if "tabla" in forma:
                    for fila in forma["tabla"]:
                        lineas_pptx.append(" | ".join(str(c) for c in fila))
            notas = (diap.get("notas_orador") or "").strip()
            if notas:
                lineas_pptx.append(f"[Notas] {notas}")
        return "\n".join(lineas_pptx)

    # .xlsx / .xlsm
    import openpyxl

    libro = openpyxl.load_workbook(str(ruta), data_only=True, read_only=True)
    try:
        lineas_xlsx: list[str] = []
        for nombre_hoja in libro.sheetnames:
            hoja = libro[nombre_hoja]
            lineas_xlsx.append(f"--- Hoja: {nombre_hoja} ---")
            for num_fila, fila in enumerate(hoja.iter_rows(values_only=True), start=1):
                valores = ["" if v is None else str(v) for v in fila]
                if any(v.strip() for v in valores):
                    lineas_xlsx.append(f"F{num_fila}: " + " | ".join(valores))
        return "\n".join(lineas_xlsx)
    finally:
        libro.close()


def obtener_esquema_documento(
    ruta_archivo: str,
    max_elementos: int = 100,
) -> dict[str, Any]:
    """
    Devuelve un indice estructural ligero (solo encabezados, diapositivas, hojas o paginas)
    con su numero de linea o indice, evitando volcar el cuerpo completo.
    """
    if max_elementos <= 0:
        raise ValueError("max_elementos debe ser mayor que cero.")

    ruta = _validar_ruta(ruta_archivo)
    sufijo = ruta.suffix.lower()
    elementos: list[dict[str, Any]] = []

    if sufijo == ".docx":
        doc = Document(str(ruta))
        for idx, parrafo in enumerate(doc.paragraphs, start=1):
            nombre_estilo = (parrafo.style.name if parrafo.style else "") or ""
            texto = parrafo.text.strip()
            es_encabezado = (
                "heading" in nombre_estilo.lower()
                or "titulo" in nombre_estilo.lower()
                or "title" in nombre_estilo.lower()
            )
            if es_encabezado and texto:
                elementos.append(
                    {
                        "linea": idx,
                        "estilo": nombre_estilo,
                        "titulo": texto[:160],
                    }
                )
            if len(elementos) >= max_elementos:
                break
        return {
            "archivo": ruta.name,
            "formato": sufijo,
            "total_parrafos": len(doc.paragraphs),
            "total_tablas": len(doc.tables),
            "elementos": elementos,
        }

    if sufijo == ".pptx":
        from .pptx_surgeon import PptxSurgeon

        cirujano = PptxSurgeon(str(ruta))
        diapositivas = cirujano.inspeccionar_diapositivas()
        for diap in diapositivas[:max_elementos]:
            textos = [
                f.get("texto_completo", "").strip()
                for f in diap.get("formas", [])
                if f.get("texto_completo", "").strip()
            ]
            elementos.append(
                {
                    "diapositiva": diap["indice"],
                    "titulo_aprox": (textos[0][:120] if textos else "(sin texto)"),
                    "total_formas": len(diap.get("formas", [])),
                }
            )
        return {
            "archivo": ruta.name,
            "formato": sufijo,
            "total_diapositivas": len(diapositivas),
            "elementos": elementos,
        }

    if sufijo in {".xlsx", ".xlsm"}:
        from .excel_surgeon import ExcelSurgeon

        hojas = ExcelSurgeon.inspect_sheets(str(ruta))
        if isinstance(hojas, dict) and "hojas" in hojas:
            lista_hojas = hojas["hojas"][:max_elementos]
        elif isinstance(hojas, list):
            lista_hojas = hojas[:max_elementos]
        else:
            lista_hojas = [hojas]
        return {
            "archivo": ruta.name,
            "formato": sufijo,
            "elementos": lista_hojas,
        }

    if sufijo == ".pdf":
        lector = PdfReader(str(ruta))
        for idx, pagina in enumerate(lector.pages[:max_elementos], start=1):
            primera_linea = ""
            for linea in (pagina.extract_text() or "").splitlines():
                if linea.strip():
                    primera_linea = linea.strip()[:140]
                    break
            elementos.append({"pagina": idx, "encabezado_aprox": primera_linea})
        return {
            "archivo": ruta.name,
            "formato": sufijo,
            "total_paginas": len(lector.pages),
            "elementos": elementos,
        }

    # .txt
    texto_txt = ruta.read_text(encoding="utf-8", errors="replace")
    lineas_txt = texto_txt.splitlines()
    patron_seccion = re.compile(r"^(#{1,6}\s+.+|\d+(?:\.\d+)*[.)]\s+.+|[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{3,60}:?)$")
    for idx, linea in enumerate(lineas_txt, start=1):
        limpia = linea.strip()
        if limpia and patron_seccion.match(limpia):
            elementos.append({"linea": idx, "titulo": limpia[:160]})
            if len(elementos) >= max_elementos:
                break
    return {
        "archivo": ruta.name,
        "formato": sufijo,
        "total_lineas": len(lineas_txt),
        "elementos": elementos,
    }


def leer_rango_documento(
    ruta_archivo: str,
    linea_inicio: int | None = None,
    linea_fin: int | None = None,
) -> dict[str, Any]:
    """
    Lee un documento en texto limpio devolviendo solo el rango de lineas solicitado
    con numeracion de linea (ej. '42: contenido').
    """
    ruta = _validar_ruta(ruta_archivo)
    texto = extraer_texto_plano_documento(ruta)
    rango = extraer_rango_lineas(texto, linea_inicio=linea_inicio, linea_fin=linea_fin)
    rango["archivo"] = ruta.name
    rango["formato"] = ruta.suffix.lower()
    return rango


def buscar_en_documento(
    ruta_archivo: str,
    consulta: str,
    lineas_contexto: int = 2,
    max_coincidencias: int = 20,
) -> dict[str, Any]:
    """
    Busca una cadena en el documento devolviendo coincidencias con contexto acotado
    y numeros de linea.
    """
    ruta = _validar_ruta(ruta_archivo)
    texto = extraer_texto_plano_documento(ruta)
    resultado = buscar_con_contexto(
        texto,
        consulta=consulta,
        lineas_contexto=lineas_contexto,
        max_coincidencias=max_coincidencias,
    )
    resultado["archivo"] = ruta.name
    resultado["formato"] = ruta.suffix.lower()
    return resultado
