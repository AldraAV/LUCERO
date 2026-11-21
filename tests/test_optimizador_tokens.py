"""
tests/test_optimizador_tokens.py — Pruebas de ahorro de tokens, paginacion,
navegacion por rangos, busqueda acotada y diffs compactos en LUCERO.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import openpyxl
import pytest
from pptx import Presentation

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.optimizador_tokens import (
    LIMITE_CARACTERES_RESPUESTA,
    buscar_con_contexto,
    extraer_rango_lineas,
    generar_diff_compacto,
    paginar_lista,
    serializar_respuesta_compacta,
    serializar_toon,
)
from src.server import (
    batch_normalize_styles,
    edit_section_layout,
    get_document_outline,
    inspect_xml_tree,
    pptx_inspect_slides,
    pptx_surgical_replace,
    pro_read_document,
    search_in_doc,
    surgical_replace,
)
from tests.test_surgeon import _crear_docx_sintetico


def test_serializar_respuesta_compacta_trunca_a_8000() -> None:
    datos_grandes = {"texto": "A" * 12000}
    salida = serializar_respuesta_compacta(datos_grandes)
    assert len(salida) <= LIMITE_CARACTERES_RESPUESTA
    parsed = json.loads(salida)
    assert parsed["truncado"] is True
    assert parsed["limite_caracteres"] == LIMITE_CARACTERES_RESPUESTA
    assert "nota_paginacion" in parsed


def test_serializar_respuesta_compacta_sin_indentacion() -> None:
    salida = serializar_respuesta_compacta({"a": 1, "b": [2, 3]})
    assert "\n" not in salida
    assert salida == '{"a":1,"b":[2,3]}'


def test_paginar_lista_y_errores() -> None:
    res = paginar_lista([10, 20, 30, 40, 50], inicio=1, limite=2)
    assert res["elementos"] == [20, 30]
    assert res["hay_mas"] is True
    assert res["siguiente_inicio"] == 3

    with pytest.raises(ValueError):
        paginar_lista([1], inicio=-1, limite=5)
    with pytest.raises(ValueError):
        paginar_lista([1], inicio=0, limite=0)


def test_extraer_rango_y_buscar_contexto() -> None:
    texto = "\n".join(f"Linea numero {i}" for i in range(1, 21))
    rango = extraer_rango_lineas(texto, linea_inicio=5, linea_fin=7)
    assert "5: Linea numero 5" in rango["contenido"]
    assert "7: Linea numero 7" in rango["contenido"]
    assert "8: Linea numero 8" not in rango["contenido"]

    busq = buscar_con_contexto(texto, consulta="numero 10", lineas_contexto=1)
    assert busq["total_coincidencias_mostradas"] == 1
    frag = busq["coincidencias"][0]["fragmento"]
    assert "9: Linea numero 9" in frag
    assert "10: Linea numero 10" in frag
    assert "11: Linea numero 11" in frag


def test_generar_diff_compacto() -> None:
    diff = generar_diff_compacto("valor antiguo", "valor nuevo", etiqueta="doc.docx")
    assert "-valor antiguo" in diff
    assert "+valor nuevo" in diff


def test_serializar_toon_ahorro_y_truncamiento() -> None:
    filas = [
        {"index": i, "paraId": f"P{i:03d}", "style": "Normal", "text": f"Parrafo {i}"}
        for i in range(30)
    ]
    datos = {"archivo": "doc.docx", "paragraphs": filas}
    toon = serializar_toon(datos)
    json_compacto = json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
    assert "paragraphs[30]{index,paraId,style,text}:" in toon
    assert len(toon) < len(json_compacto)

    largo = {"items": [{"id": i, "valor": "X" * 300} for i in range(50)]}
    toon_trunc = serializar_toon(largo)
    assert len(toon_trunc) <= LIMITE_CARACTERES_RESPUESTA
    assert "truncado: true" in toon_trunc


def test_outline_y_search_en_txt(tmp_path: Path) -> None:
    archivo = tmp_path / "notas.txt"
    archivo.write_text(
        "# Introduccion\nTexto inicial.\nDetalle extra.\n# Metodologia\nUso de agua pura.\nCierre.\n",
        encoding="utf-8",
    )
    res_outline = get_document_outline(str(archivo))
    assert "formato: .txt" in res_outline
    assert "elementos[2]{linea,titulo}:" in res_outline

    res_search = json.loads(search_in_doc(str(archivo), query="agua pura", context_lines=1))
    assert res_search["total_coincidencias_mostradas"] == 1
    assert "5: Uso de agua pura." in res_search["coincidencias"][0]["fragmento"]


def test_outline_y_search_en_docx(tmp_path: Path) -> None:
    docx_path = tmp_path / "prueba.docx"
    _crear_docx_sintetico(docx_path)

    res_light = inspect_xml_tree(str(docx_path), max_paragraphs=2, offset=0, lightweight=True)
    assert "offset: 0" in res_light
    assert "paragraphs[2]{index,paraId,style,text}:" in res_light
    assert "runs" not in res_light

    res_rep = json.loads(
        surgical_replace(
            docx_path=str(docx_path),
            target_text="Etiqueta en negrita:",
            replacement_text="Etiqueta Editada:",
        )
    )
    assert res_rep["success"] is True
    assert "-Etiqueta en negrita:" in res_rep["diff"]
    assert "+Etiqueta Editada:" in res_rep["diff"]


def test_outline_y_cirugia_en_pptx(tmp_path: Path) -> None:
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Titulo Diapositiva 1"
    slide.placeholders[1].text = "Contenido original"
    pptx_path = tmp_path / "demo.pptx"
    prs.save(str(pptx_path))

    res_outline = get_document_outline(str(pptx_path))
    assert "total_diapositivas: 1" in res_outline
    assert "Titulo Diapositiva 1" in res_outline

    res_insp = pptx_inspect_slides(str(pptx_path), offset=0, limit=1)
    assert "total_diapositivas: 1" in res_insp

    res_rep = json.loads(
        pptx_surgical_replace(
            pptx_path=str(pptx_path),
            search_text="Contenido original",
            replace_text="Contenido optimizado",
        )
    )
    assert res_rep["exito"] is True
    assert "+Contenido optimizado" in res_rep["diff"]


def test_outline_en_xlsx(tmp_path: Path) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Resumen"
    ws["A1"] = "Indicador"
    ws["B1"] = "Valor"
    ws["A2"] = "Eficiencia"
    ws["B2"] = 99
    xlsx_path = tmp_path / "tabla.xlsx"
    wb.save(str(xlsx_path))
    wb.close()

    res_outline = get_document_outline(str(xlsx_path))
    assert "formato: .xlsx" in res_outline

    res_search = json.loads(search_in_doc(str(xlsx_path), query="Eficiencia"))
    assert res_search["total_coincidencias_mostradas"] == 1


@pytest.mark.asyncio
async def test_pro_read_document_rangos_y_busqueda(tmp_path: Path) -> None:
    txt_path = tmp_path / "largo.txt"
    txt_path.write_text("\n".join(f"Linea {i}" for i in range(1, 51)), encoding="utf-8")

    res_rango = json.loads(
        await pro_read_document(str(txt_path), start_line=10, end_line=12)
    )
    assert res_rango["success"] is True
    assert "10: Linea 10" in res_rango["data"]["contenido"]
    assert "13: Linea 13" not in res_rango["data"]["contenido"]

    res_busq = json.loads(
        await pro_read_document(str(txt_path), search_query="Linea 25")
    )
    assert res_busq["success"] is True
    assert res_busq["data"]["total_coincidencias_mostradas"] == 1


def test_edit_section_layout_y_batch_normalize_styles(tmp_path: Path) -> None:
    import zipfile
    from docx import Document as DocxDoc
    from lxml import etree
    from src.utils import NS

    docx_path = tmp_path / "apa_prueba.docx"
    doc = DocxDoc()
    doc.add_paragraph("Primer parrafo de prueba.")
    doc.add_paragraph("Segundo parrafo de prueba.")
    doc.save(str(docx_path))

    res_layout = edit_section_layout(
        file_path=str(docx_path),
        margins_twips={"top": 1440, "bottom": 1440, "left": 1440, "right": 1440},
        page_size_twips={"w": 12240, "h": 15840},
        enforce_apa_page_number=True,
    )
    assert res_layout.startswith("OK:")
    assert "1 secciones" in res_layout
    assert "1 encabezados" in res_layout

    res_styles = batch_normalize_styles(
        file_path=str(docx_path),
        target_xpath="//w:body/w:p",
        update_doc_defaults=True,
        set_font="Times New Roman",
        set_size_half_pts=24,
        set_align="left",
        set_line_spacing=480,
        set_space_after=0,
    )
    assert res_styles.startswith("OK:")
    assert "nodos actualizados" in res_styles

    with zipfile.ZipFile(docx_path) as z:
        doc_xml = etree.fromstring(z.read("word/document.xml"))
        pg_mar = doc_xml.find(f".//{{{NS['w']}}}sectPr/{{{NS['w']}}}pgMar")
        assert pg_mar is not None
        assert pg_mar.get(f"{{{NS['w']}}}top") == "1440"
        pg_num = doc_xml.find(f".//{{{NS['w']}}}sectPr/{{{NS['w']}}}pgNumType")
        assert pg_num is not None
        assert pg_num.get(f"{{{NS['w']}}}start") == "1"

        headers = [n for n in z.namelist() if n.startswith("word/header") and n.endswith(".xml")]
        assert len(headers) >= 1
        hdr_xml = etree.fromstring(z.read(headers[0]))
        fld = hdr_xml.find(f".//{{{NS['w']}}}fldSimple")
        assert fld is not None
        assert fld.get(f"{{{NS['w']}}}instr") == "PAGE"

        styles_xml = etree.fromstring(z.read("word/styles.xml"))
        rfonts_def = styles_xml.find(f".//{{{NS['w']}}}docDefaults//{{{NS['w']}}}rFonts")
        assert rfonts_def is not None
        assert rfonts_def.get(f"{{{NS['w']}}}ascii") == "Times New Roman"
