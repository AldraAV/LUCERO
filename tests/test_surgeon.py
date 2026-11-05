"""
tests/test_surgeon.py — Suite de pruebas para DocxSurgeon y plantillas APA.
Usa el archivo Caso_practico_u3_FINAL.docx como fixture de prueba real.
"""

from __future__ import annotations

import shutil

# Ajuste de path para imports relativos
import sys
from pathlib import Path

import pytest
from lxml import etree

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.apa_templates import (
    apa_body_paragraph,
    apa_centered_text,
    apa_figure_label,
    apa_figure_note,
    apa_header_page_number,
    apa_heading1,
    apa_heading2,
    apa_heading3,
    apa_heading4,
    apa_heading5,
    apa_in_text_citation,
    apa_page_break,
    apa_reference_entry,
)
from src.surgeon import DocxSurgeon
from src.utils import qn

# ─────────────────────────────────────────────────────────────────────────────
# FIXTURE: copia temporal del DOCX real
# ─────────────────────────────────────────────────────────────────────────────
REAL_DOCX = Path(r"C:\Users\carde\Desktop\MUACK\Caso_practico_u3_FINAL.docx")


def _crear_docx_sintetico(destino: Path) -> Path:
    import zipfile
    content_types = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""
    rels = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
    doc_rels = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>"""
    doc_xml = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml">
  <w:body>
    <w:p w14:paraId="12345678">
      <w:pPr>
        <w:pStyle w:val="Normal"/>
        <w:jc w:val="both"/>
      </w:pPr>
      <w:r><w:rPr><w:b/></w:rPr><w:t>Etiqueta en negrita:</w:t></w:r>
      <w:r><w:t xml:space="preserve"> Texto normal con datos viejos.</w:t></w:r>
    </w:p>
    <w:p w14:paraId="87654321">
      <w:r><w:t>Repetido aqui y Repetido alla.</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t>Texto de parrafo tercero largo para pruebas de inspeccion.</w:t></w:r>
    </w:p>
  </w:body>
</w:document>"""
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        z.writestr("word/document.xml", doc_xml)
    return destino


@pytest.fixture
def tmp_docx(tmp_path: Path) -> Path:
    """Copia el DOCX real o genera uno sintético válido para pruebas."""
    dest = tmp_path / "test.docx"
    if REAL_DOCX.exists():
        shutil.copy2(REAL_DOCX, dest)
    else:
        _crear_docx_sintetico(dest)
    return dest


@pytest.fixture
def surgeon(tmp_docx: Path) -> DocxSurgeon:
    return DocxSurgeon(tmp_docx)


# ─────────────────────────────────────────────────────────────────────────────
# TESTS: DocxSurgeon — Inspección
# ─────────────────────────────────────────────────────────────────────────────

class TestInspection:
    def test_tree_loads(self, surgeon: DocxSurgeon):
        """El árbol XML debe cargarse sin errores."""
        tree = surgeon.tree
        assert tree is not None
        assert tree.tag is not None

    def test_inspect_tree_returns_list(self, surgeon: DocxSurgeon):
        """inspect_tree debe retornar una lista de dicts."""
        result = surgeon.inspect_tree(max_paragraphs=10)
        assert isinstance(result, list)
        assert len(result) <= 10

    def test_inspect_tree_structure(self, surgeon: DocxSurgeon):
        """Cada entrada debe tener las claves requeridas."""
        result = surgeon.inspect_tree(max_paragraphs=5)
        required_keys = {"para_index", "style", "text", "runs", "xpath"}
        for entry in result:
            assert required_keys.issubset(entry.keys()), \
                f"Faltan claves en entrada: {set(entry.keys())}"

    def test_runs_have_format(self, surgeon: DocxSurgeon):
        """Los runs deben incluir información de formato."""
        result = surgeon.inspect_tree(max_paragraphs=20)
        for para in result:
            for run in para["runs"]:
                assert "format" in run
                assert "bold" in run["format"]
                assert "italic" in run["format"]

    def test_get_styles_list(self, surgeon: DocxSurgeon):
        """get_styles_list debe retornar una lista de strings no vacía."""
        styles = surgeon.get_styles_list()
        assert isinstance(styles, list)
        assert len(styles) > 0
        assert all(isinstance(s, str) for s in styles)


# ─────────────────────────────────────────────────────────────────────────────
# TESTS: DocxSurgeon — Reemplazo quirúrgico
# ─────────────────────────────────────────────────────────────────────────────

class TestSurgicalReplace:
    def test_replace_simple(self, surgeon: DocxSurgeon, tmp_docx: Path):
        """Debe encontrar y reemplazar texto existente."""
        # Primero obtener un texto real del documento
        paragraphs = surgeon.inspect_tree(max_paragraphs=50)
        # Buscar un párrafo con texto
        target = None
        for para in paragraphs:
            if len(para["text"]) > 10:
                target = para["text"][:15]
                break

        if not target:
            pytest.skip("No se encontró texto suficiente en el documento")

        result = surgeon.surgical_replace(target, target + " [EDITADO]")
        assert result["occurrences_replaced"] >= 1

    def test_replace_preserves_format(self, surgeon: DocxSurgeon):
        """El reemplazo no debe alterar los tags <w:rPr>."""
        paragraphs = surgeon.inspect_tree(max_paragraphs=30)
        # Buscar run en negrita
        bold_run = None
        for para in paragraphs:
            for run in para["runs"]:
                if run["format"].get("bold") and len(run["text"]) > 5:
                    bold_run = run
                    break
            if bold_run:
                break

        if not bold_run:
            pytest.skip("No se encontró run en negrita")

        target = bold_run["text"][:10]
        surgeon.surgical_replace(target, target)

        # Verificar que el run sigue en negrita
        para_nodes = surgeon.tree.findall(f".//{qn('w', 'p')}")
        found_bold = False
        for para in para_nodes:
            for run in para.findall(qn("w", "r")):
                rpr = run.find(qn("w", "rPr"))
                if rpr is not None and rpr.find(qn("w", "b")) is not None:
                    found_bold = True
                    break
        assert found_bold, "Se perdió el formato negrita tras el reemplazo"

    def test_replace_not_found(self, surgeon: DocxSurgeon):
        """Si el texto no existe, should report 0 replacements."""
        result = surgeon.surgical_replace(
            "TEXTO_QUE_NO_EXISTE_JAMAS_12345",
            "reemplazo"
        )
        assert result["occurrences_replaced"] == 0

    def test_no_dirty_if_no_change(self, surgeon: DocxSurgeon):
        """Si no hubo reemplazo, dirty debe ser False."""
        surgeon.surgical_replace("IMPOSIBLE_ENCONTRAR_XYZ", "nada")
        assert not surgeon._dirty


# ─────────────────────────────────────────────────────────────────────────────
# TESTS: DocxSurgeon — Commit
# ─────────────────────────────────────────────────────────────────────────────

class TestCommit:
    def test_commit_creates_valid_zip(self, surgeon: DocxSurgeon, tmp_path: Path):
        """El DOCX resultante debe ser un ZIP válido con document.xml."""
        import zipfile
        output = tmp_path / "output.docx"
        # Forzar un cambio mínimo
        paragraphs = surgeon.inspect_tree(max_paragraphs=10)
        if paragraphs and paragraphs[0]["text"]:
            t = paragraphs[0]["text"][:5]
            surgeon.surgical_replace(t, t)

        surgeon._dirty = True
        result = surgeon.commit_changes(output)
        assert result["committed"] is True
        assert output.exists()

        with zipfile.ZipFile(output) as z:
            names = z.namelist()
            assert "word/document.xml" in names
            assert "[Content_Types].xml" in names

    def test_commit_no_dirty_skips(self, surgeon: DocxSurgeon, tmp_path: Path):
        """commit sin cambios debe retornar committed=False."""
        result = surgeon.commit_changes(tmp_path / "no_change.docx")
        assert result["committed"] is False


# ─────────────────────────────────────────────────────────────────────────────
# TESTS: Plantillas APA
# ─────────────────────────────────────────────────────────────────────────────

class TestApaTemplates:
    def test_heading1_is_element(self):
        el = apa_heading1("Introducción")
        assert isinstance(el, etree._Element)
        assert el.tag.endswith("}p")

    def test_heading1_has_bold_run(self):
        el = apa_heading1("Introducción")
        runs = el.findall(f".//{qn('w', 'r')}")
        has_bold = any(
            r.find(qn("w", "rPr")) is not None and
            r.find(qn("w", "rPr")).find(qn("w", "b")) is not None
            for r in runs
        )
        assert has_bold, "El heading1 debe tener run en negrita"

    def test_heading1_centered(self):
        el = apa_heading1("Título")
        ppr = el.find(qn("w", "pPr"))
        assert ppr is not None
        jc = ppr.find(qn("w", "jc"))
        assert jc is not None
        assert jc.get(qn("w", "val")) == "center"

    def test_figure_label_returns_two_elements(self):
        result = apa_figure_label(3, "Vista de la tabla usuarios")
        assert len(result) == 2

    def test_figure_label_text_correct(self):
        result = apa_figure_label(5, "Mi título")
        # Primer elemento debe contener "Figura 5"
        texts = [
            t.text for t in result[0].iter(qn("w", "t"))
        ]
        assert any("Figura 5" in (t or "") for t in texts)

    def test_figure_note_has_italic_nota(self):
        el = apa_figure_note("Esta es la nota.")
        runs = el.findall(f".//{qn('w', 'r')}")
        italic_run = None
        for r in runs:
            rpr = r.find(qn("w", "rPr"))
            if rpr is not None and rpr.find(qn("w", "i")) is not None:
                t = r.find(qn("w", "t"))
                if t is not None and "Nota" in (t.text or ""):
                    italic_run = r
                    break
        assert italic_run is not None, "La nota debe tener 'Nota.' en cursiva"

    def test_reference_has_hanging_indent(self):
        el = apa_reference_entry("García, J. (2022). Título del libro. Editorial.")
        ppr = el.find(qn("w", "pPr"))
        assert ppr is not None
        ind = ppr.find(qn("w", "ind"))
        assert ind is not None
        assert ind.get(qn("w", "hanging")) is not None

    def test_in_text_citation_format(self):
        result = apa_in_text_citation("García", 2022)
        assert result == "(García, 2022)"
        with_page = apa_in_text_citation("García", 2022, "45")
        assert with_page == "(García, 2022, p. 45)"

    def test_body_paragraph_double_spacing(self):
        el = apa_body_paragraph("Texto de prueba.")
        ppr = el.find(qn("w", "pPr"))
        assert ppr is not None
        spacing = ppr.find(qn("w", "spacing"))
        assert spacing is not None
        assert spacing.get(qn("w", "line")) == "480"   # doble espacio


# ─────────────────────────────────────────────────────────────────────────────
# TESTS: XPath
# ─────────────────────────────────────────────────────────────────────────────

class TestXPath:
    def test_find_by_xpath_body(self, surgeon: DocxSurgeon):
        """XPath básico debe encontrar el body."""
        results = surgeon.find_by_xpath("//w:body")
        assert len(results) == 1

    def test_find_paragraphs(self, surgeon: DocxSurgeon):
        """Debe encontrar al menos un párrafo."""
        results = surgeon.find_by_xpath("//w:p")
        assert len(results) > 0


# ─────────────────────────────────────────────────────────────────────────────
# TESTS: Motor de desplazamientos, clonación y lotes atómicos (Zero format loss)
# ─────────────────────────────────────────────────────────────────────────────

class TestMotorDesplazamientosYClonado:
    def test_reemplazo_no_destruye_negrita_etiqueta(self, surgeon: DocxSurgeon):
        """
        Al reemplazar texto normal en 'Etiqueta en negrita: Texto normal...',
        la etiqueta debe mantenerse en negrita y el nuevo texto NO debe volverse negrita.
        """
        resultado = surgeon.surgical_replace(
            target_text="Texto normal con datos viejos.",
            replacement_text="Texto normal con datos NUEVOS actualizados.",
        )
        assert resultado["occurrences_replaced"] == 1

        body = surgeon.tree.find(qn("w", "body"))
        p = body.findall(f".//{qn('w', 'p')}")[0]
        runs = p.findall(qn("w", "r"))

        # El primer run (Etiqueta en negrita:) debe seguir teniendo w:b
        rpr0 = runs[0].find(qn("w", "rPr"))
        assert rpr0 is not None and rpr0.find(qn("w", "b")) is not None
        assert "Etiqueta en negrita:" in (runs[0].find(qn("w", "t")).text or "")

        # El segundo run NO debe tener w:b
        rpr1 = runs[1].find(qn("w", "rPr"))
        b1 = rpr1.find(qn("w", "b")) if rpr1 is not None else None
        assert b1 is None
        assert "datos NUEVOS" in (runs[1].find(qn("w", "t")).text or "")

    def test_occurrence_exacta(self, surgeon: DocxSurgeon):
        """occurrence=2 debe reemplazar ÚNICAMENTE la segunda aparición."""
        res = surgeon.surgical_replace(
            target_text="Repetido",
            replacement_text="UNICO",
            occurrence=2,
        )
        assert res["occurrences_found"] == 2
        assert res["occurrences_replaced"] == 1
        # El texto del párrafo debe ser "Repetido aqui y UNICO alla."
        body = surgeon.tree.find(qn("w", "body"))
        p1 = body.findall(f".//{qn('w', 'p')}")[1]
        texto = surgeon.texto_parrafo(p1)
        assert texto == "Repetido aqui y UNICO alla."

    def test_insertar_parrafo_clonado(self, surgeon: DocxSurgeon):
        """insertar_parrafo_clonado clona pPr y hereda formato de runs."""
        res = surgeon.insertar_parrafo_clonado(
            texto_ancla="Etiqueta en negrita:",
            segmentos=["Nueva viñeta:", " contenido clonado."],
            posicion="despues",
        )
        assert res["success"] is True

        body = surgeon.tree.find(qn("w", "body"))
        parrafos = body.findall(f".//{qn('w', 'p')}")
        assert len(parrafos) >= 4
        nuevo_p = parrafos[1]

        # Verificar que heredo w:jc both de pPr
        ppr = nuevo_p.find(qn("w", "pPr"))
        assert ppr is not None
        jc = ppr.find(qn("w", "jc"))
        assert jc is not None and jc.get(qn("w", "val")) == "both"

        # Verificar que el segmento 0 tiene negrita y el 1 no
        runs = nuevo_p.findall(qn("w", "r"))
        assert len(runs) == 2
        rpr0 = runs[0].find(qn("w", "rPr"))
        assert rpr0 is not None and rpr0.find(qn("w", "b")) is not None
        assert runs[0].find(qn("w", "t")).text == "Nueva viñeta:"

        rpr1 = runs[1].find(qn("w", "rPr"))
        b1 = rpr1.find(qn("w", "b")) if rpr1 is not None else None
        assert b1 is None

    def test_aplicar_lote_atomico_fallo_no_escribe(self, surgeon: DocxSurgeon):
        """Si una operación falla, aplicar_lote descarta todo y dirty es False."""
        operaciones = [
            {"tipo": "reemplazar", "objetivo": "Etiqueta en negrita:", "reemplazo": "Cambio preliminar"},
            {"tipo": "reemplazar", "objetivo": "TEXTO_QUE_JAMAS_EXISTE", "reemplazo": "Falla"},
        ]
        res = surgeon.aplicar_lote(operaciones)
        assert res["exito"] is False
        assert res["fallo_en"] == 2
        assert surgeon._dirty is False
        # El documento original debe estar intacto
        body = surgeon.tree.find(qn("w", "body"))
        p0 = body.findall(f".//{qn('w', 'p')}")[0]
        assert "Etiqueta en negrita:" in surgeon.texto_parrafo(p0)

    def test_commit_genera_respaldo(self, surgeon: DocxSurgeon, tmp_path: Path):
        """commit_changes sobreescribiendo el original genera archivo de respaldo."""
        surgeon.surgical_replace("datos viejos", "datos respaldados")
        res = surgeon.commit_changes()
        assert res["committed"] is True
        assert res["backup_path"] is not None
        assert Path(res["backup_path"]).exists()

    def test_ensamblar_plantilla_maestra_sintetica(self, tmp_path: Path):
        """ensamblar_plantilla_maestra une portada, preserva índice e inyecta cuerpo."""
        p_plantilla = tmp_path / "plantilla.docx"
        p_hoja = tmp_path / "hoja.docx"
        p_cuerpo = tmp_path / "cuerpo.docx"

        # Crear docx auxiliares sintéticos
        _crear_docx_sintetico(p_plantilla)
        _crear_docx_sintetico(p_hoja)
        _crear_docx_sintetico(p_cuerpo)

        # Configurar plantilla con Índice y Resumen
        s_pl = DocxSurgeon(p_plantilla)
        s_pl.surgical_replace("Etiqueta en negrita:", "Portada vieja")
        s_pl.surgical_replace("Repetido aqui y Repetido alla.", "Índice de materias")
        s_pl.surgical_replace("Texto de parrafo tercero largo para pruebas de inspeccion.", "Resumen viejo")
        s_pl.commit_changes()

        # Configurar cuerpo con Resumen nuevo y texto EmpleaTEC
        s_cu = DocxSurgeon(p_cuerpo)
        s_cu.surgical_replace("Etiqueta en negrita:", "Resumen")
        s_cu.surgical_replace("Texto normal con datos viejos.", " El proyecto EmpleaTEC inicia aqui.")
        s_cu.commit_changes()

        # Ejecutar ensamblado en s_pl
        cirujano = DocxSurgeon(p_plantilla)
        res = cirujano.ensamblar_plantilla_maestra(
            ruta_hoja_presentacion=p_hoja,
            ruta_contenido_cuerpo=p_cuerpo,
            ancla_indice="Índice",
            ancla_cuerpo_destino="Resumen viejo",
            ancla_cuerpo_origen="Resumen",
            identificador_cuerpo_origen="EmpleaTEC",
        )
        assert res["success"] is True
        assert res["cuerpo_elementos"] >= 1
        commit = cirujano.commit_changes()
        assert commit["committed"] is True

    def test_exportar_a_markdown(self, surgeon: DocxSurgeon, tmp_path: Path):
        """exportar_a_markdown genera archivo Markdown sin alterar el DOCX original."""
        salida_md = tmp_path / "resultado.md"
        res = surgeon.exportar_a_markdown(salida_md)
        assert res["success"] is True
        assert salida_md.exists()
        assert salida_md.stat().st_size > 0
        contenido = salida_md.read_text(encoding="utf-8")
        assert len(contenido) > 0
        assert surgeon.path.exists()


# ─────────────────────────────────────────────────────────────────────────────
# TESTS: Jerarquía APA 7, encabezados y regresión (M8, M9, M10, M11)
# ─────────────────────────────────────────────────────────────────────────────

class TestApaJerarquiaYRegresion:
    def test_heading4_nivel_apa7(self):
        el = apa_heading4("Metodología")
        ppr = el.find(qn("w", "pPr"))
        assert ppr is not None
        ind = ppr.find(qn("w", "ind"))
        assert ind is not None and ind.get(qn("w", "firstLine")) == "720"
        texto = "".join((t.text or "") for t in el.iter(qn("w", "t")))
        assert texto.endswith(".")

    def test_heading5_nivel_apa7(self):
        el = apa_heading5("Participantes")
        ppr = el.find(qn("w", "pPr"))
        assert ppr is not None
        ind = ppr.find(qn("w", "ind"))
        assert ind is not None and ind.get(qn("w", "firstLine")) == "720"
        runs = el.findall(qn("w", "r"))
        assert any(
            r.find(qn("w", "rPr")) is not None
            and r.find(qn("w", "rPr")).find(qn("w", "b")) is not None
            and r.find(qn("w", "rPr")).find(qn("w", "i")) is not None
            for r in runs
        )

    def test_centered_text_portada(self):
        el = apa_centered_text("Título de Portada", bold=True)
        ppr = el.find(qn("w", "pPr"))
        assert ppr is not None
        jc = ppr.find(qn("w", "jc"))
        assert jc is not None and jc.get(qn("w", "val")) == "center"

    def test_salto_de_pagina(self):
        el = apa_page_break()
        br = el.find(f".//{qn('w', 'br')}")
        assert br is not None
        assert br.get(qn("w", "type")) == "page"

    def test_referencia_cursiva_parcial(self):
        texto = "García, J. (2022). Título del libro. Editorial."
        el = apa_reference_entry(texto, cursiva="Título del libro")
        runs = el.findall(qn("w", "r"))
        run_cursiva = None
        for r in runs:
            rpr = r.find(qn("w", "rPr"))
            if rpr is not None and rpr.find(qn("w", "i")) is not None:
                t = r.find(qn("w", "t"))
                if t is not None and t.text == "Título del libro":
                    run_cursiva = r
                    break
        assert run_cursiva is not None

    def test_header_page_number(self):
        hdr = apa_header_page_number()
        jc = hdr.find(f".//{qn('w', 'jc')}")
        assert jc is not None and jc.get(qn("w", "val")) == "right"
        fld = hdr.find(f".//{qn('w', 'fldSimple')}")
        assert fld is not None and fld.get(qn("w", "instr")) == "PAGE"


