"""
tests/test_server_mcp_e2e.py — Pruebas de extremo a extremo para las herramientas MCP de server.py.
Valida la ejecución real de las tools registradas en FastMCP.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.server import (
    commit_changes,
    inject_apa_structure,
    inspect_excel_cells,
    inspect_excel_sheets,
    inspect_xml_tree,
    list_apa_templates,
    pro_read_document,
    pro_write_document,
    run_xpath,
    surgical_inject_excel_table,
    surgical_replace,
    surgical_replace_excel_cell,
    surgical_search_replace_excel,
    surgical_style_edit,
    surgical_inject_image,
)
from tests.test_surgeon import _crear_docx_sintetico


@pytest.fixture
def docx_mcp(tmp_path: Path) -> Path:
    dest = tmp_path / "documento_mcp.docx"
    _crear_docx_sintetico(dest)
    return dest


@pytest.fixture
def xlsx_mcp(tmp_path: Path) -> Path:
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Datos"
    ws["A1"] = "Clave"
    ws["B1"] = "Total"
    ws["A2"] = "Alfa"
    ws["B2"] = 100
    ruta = tmp_path / "libro_mcp.xlsx"
    wb.save(str(ruta))
    wb.close()
    return ruta


# ─────────────────────────────────────────────────────────────────────────────
# PRUEBAS E2E DE HERRAMIENTAS DOCX MCP
# ─────────────────────────────────────────────────────────────────────────────

def test_e2e_inspect_xml_tree(docx_mcp: Path) -> None:
    res = inspect_xml_tree(str(docx_mcp), max_paragraphs=5)
    assert "error:" not in res.lower()
    assert "Etiqueta en negrita:" in res


def test_e2e_list_apa_templates() -> None:
    res = list_apa_templates()
    assert "heading1" in res
    assert "body_paragraph" in res
    assert "reference" in res


def test_e2e_run_xpath(docx_mcp: Path) -> None:
    res = run_xpath(str(docx_mcp), "//w:body//w:p")
    assert "error:" not in res.lower()
    assert "nodos" in res.lower() or "encontrados" in res.lower() or "coincidencias" in res.lower() or "tag:" in res.lower()


def test_e2e_surgical_replace_and_commit(docx_mcp: Path, tmp_path: Path) -> None:
    res_rep = surgical_replace(
        docx_path=str(docx_mcp),
        target_text="Etiqueta en negrita:",
        replacement_text="Etiqueta Actualizada:",
    )
    assert "error:" not in res_rep.lower()
    assert "1" in res_rep

    salida = tmp_path / "comprobado.docx"
    res_com = commit_changes(docx_path=str(docx_mcp), output_path=str(salida))
    assert "error:" not in res_com.lower()
    assert salida.exists()
    assert salida.stat().st_size > 0


def test_e2e_surgical_style_edit(docx_mcp: Path) -> None:
    res = surgical_style_edit(
        docx_path=str(docx_mcp),
        xpath_expr="(//w:body//w:p)[1]",
        properties={"align": "center", "bold": True},
    )
    assert "error:" not in res.lower()


def test_e2e_inject_apa_structure(docx_mcp: Path) -> None:
    res = inject_apa_structure(
        docx_path=str(docx_mcp),
        anchor_text="Etiqueta en negrita:",
        template_type="heading1",
        content="Sección Uno",
        position="after",
    )
    assert "error:" not in res.lower()
    assert "true" in res.lower() or "success" in res.lower() or "inyectados" in res.lower()


@pytest.mark.anyio
async def test_e2e_pro_write_and_read_document(tmp_path: Path) -> None:
    archivo_nuevo = tmp_path / "apa_generado.docx"
    contenido_md = "# Título Principal\n\n## Subtítulo Metodológico\n\nEste es un párrafo en formato APA 7."
    res_write = await pro_write_document(
        file_path=str(archivo_nuevo),
        content=contenido_md,
        format="docx",
    )
    assert "error" not in res_write.lower() or '"success": true' in res_write.lower()
    assert archivo_nuevo.exists()

    res_read = await pro_read_document(
        file_path=str(archivo_nuevo),
        extract_type="text",
    )
    assert "Título Principal" in res_read


# ─────────────────────────────────────────────────────────────────────────────
# PRUEBAS E2E DE HERRAMIENTAS XLSX MCP
# ─────────────────────────────────────────────────────────────────────────────

def test_e2e_inspect_excel_sheets(xlsx_mcp: Path) -> None:
    res = inspect_excel_sheets(str(xlsx_mcp))
    assert "error:" not in res.lower()
    assert "Datos" in res
    assert "total_hojas: 1" in res


def test_e2e_inspect_excel_cells(xlsx_mcp: Path) -> None:
    res = inspect_excel_cells(str(xlsx_mcp), sheet_name="Datos", cell_range="A1:B2")
    assert "error:" not in res.lower()
    assert "Clave" in res
    assert "100" in res


def test_e2e_surgical_replace_excel_cell(xlsx_mcp: Path, tmp_path: Path) -> None:
    salida = tmp_path / "libro_editado.xlsx"
    res = surgical_replace_excel_cell(
        excel_path=str(xlsx_mcp),
        coordinate="B2",
        new_value="500",
        sheet_name="Datos",
        output_path=str(salida),
    )
    assert "error:" not in res.lower()
    assert "500" in res
    assert salida.exists()


def test_e2e_surgical_inject_excel_table(xlsx_mcp: Path, tmp_path: Path) -> None:
    salida = tmp_path / "libro_tabla.xlsx"
    res = surgical_inject_excel_table(
        excel_path=str(xlsx_mcp),
        start_cell="A5",
        headers=["Métrica", "Puntaje"],
        rows=[["Velocidad", 95], ["Precisión", 99]],
        sheet_name="Datos",
        table_name="MetricasRendimiento",
        output_path=str(salida),
    )
    assert "error:" not in res.lower()
    assert "total_filas_datos: 2" in res
    assert salida.exists()


def test_e2e_surgical_search_replace_excel(xlsx_mcp: Path, tmp_path: Path) -> None:
    salida = tmp_path / "libro_reemplazado.xlsx"
    res = surgical_search_replace_excel(
        excel_path=str(xlsx_mcp),
        search_text="Alfa",
        replace_text="Omega",
        output_path=str(salida),
    )
    assert "error:" not in res.lower()
    assert "total_reemplazos: 1" in res
    assert salida.exists()


def test_e2e_surgical_inject_image(docx_mcp: Path, tmp_path: Path) -> None:
    """Valida la herramienta MCP surgical_inject_image con cálculo automático de aspecto."""
    from PIL import Image as PILImage
    img_path = tmp_path / "foto.png"
    img = PILImage.new("RGBA", (300, 150), color=(225, 29, 72, 255))
    img.save(str(img_path), "PNG")

    salida = tmp_path / "docx_inyectado.docx"
    res = surgical_inject_image(
        docx_path=str(docx_mcp),
        xpath_expr="//w:body//w:p[1]",
        new_image_path=str(img_path),
        output_path=str(salida),
    )
    assert "error:" not in res.lower()
    assert "success: true" in res.lower() or '"success": true' in res.lower()
    assert salida.exists()
    assert salida.stat().st_size > 0
