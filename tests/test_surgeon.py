"""
tests/test_surgeon.py — Suite de pruebas para DocxSurgeon y plantillas APA.
Usa el archivo Caso_practico_u3_FINAL.docx como fixture de prueba real.
"""

from __future__ import annotations

import copy
import shutil
import tempfile
from pathlib import Path

import pytest
from lxml import etree

# Ajuste de path para imports relativos
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.surgeon import DocxSurgeon
from src.apa_templates import (
    apa_heading1,
    apa_heading2,
    apa_figure_label,
    apa_figure_note,
    apa_reference_entry,
    apa_body_paragraph,
    apa_in_text_citation,
)
from src.utils import NS, qn


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURE: copia temporal del DOCX real
# ─────────────────────────────────────────────────────────────────────────────
REAL_DOCX = Path(r"C:\Users\carde\Desktop\MUACK\Caso_practico_u3_FINAL.docx")


@pytest.fixture
def tmp_docx(tmp_path: Path) -> Path:
    """Copia el DOCX real a un directorio temporal para no modificar el original."""
    if not REAL_DOCX.exists():
        pytest.skip(f"Archivo de prueba no encontrado: {REAL_DOCX}")
    dest = tmp_path / "test.docx"
    shutil.copy2(REAL_DOCX, dest)
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
        results = surgeon.find_by_xpath(
            f"//{{{NS['w']}}}body"
        )
        assert len(results) == 1

    def test_find_paragraphs(self, surgeon: DocxSurgeon):
        """Debe encontrar al menos un párrafo."""
        results = surgeon.find_by_xpath(
            f"//{{{NS['w']}}}p"
        )
        assert len(results) > 0
