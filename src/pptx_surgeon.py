"""
pptx_surgeon.py — Cirujano Quirurgico para Presentaciones PowerPoint (PPTX) y PPT-Master.
Integracion nativa de inspeccion, reemplazo quirurgico de texto, inyeccion de imagenes,
compilacion desde SVG con DrawingML, renderizado de formulas LaTeX y conversion a Markdown.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Rutas internas hacia ppt_master_integration
RUTA_LUCERO = Path(__file__).resolve().parent.parent
RUTA_PPT_MASTER = RUTA_LUCERO / "ppt_master_integration"
RUTA_PPT_MASTER_SCRIPTS = RUTA_PPT_MASTER / "skills" / "ppt-master" / "scripts"

if str(RUTA_PPT_MASTER_SCRIPTS) not in sys.path and RUTA_PPT_MASTER_SCRIPTS.exists():
    sys.path.insert(0, str(RUTA_PPT_MASTER_SCRIPTS))

# Importaciones condicionales de librerias de soporte
try:
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    from pptx.util import Cm, Inches, Pt
except ImportError:
    Presentation = None
    Inches = Pt = Cm = None
    MSO_SHAPE_TYPE = None

try:
    from svg_to_pptx.pptx_builder import create_pptx_with_native_svg
except ImportError:
    create_pptx_with_native_svg = None

try:
    import latex_render
except ImportError:
    latex_render = None

try:
    from source_to_md.ppt_to_md import convert_presentation_to_markdown
except ImportError:
    convert_presentation_to_markdown = None

try:
    from pptx_to_svg import convert_pptx_to_svg
except ImportError:
    convert_pptx_to_svg = None

from .utils import get_logger

registro = get_logger("lucero.pptx_surgeon")


class PptxSurgeon:
    """Motor quirurgico para presentaciones PowerPoint (.pptx).
    Permite inspeccionar diapositivas, reemplazar texto preservando formato exacto,
    inyectar imagenes/formulas metricamente, y orquestar herramientas de PPT-Master."""

    def __init__(self, ruta_pptx: str | Path | None = None) -> None:
        self.ruta: Path | None = Path(ruta_pptx) if ruta_pptx else None
        self._presentacion: Any | None = None
        self._modificado: bool = False

        if self.ruta:
            if not self.ruta.exists():
                raise FileNotFoundError(f"Archivo PPTX no encontrado: {self.ruta}")
            if Presentation is None:
                raise RuntimeError("python-pptx no esta instalado en el entorno.")
            self._presentacion = Presentation(str(self.ruta))
            registro.info("PptxSurgeon cargado para presentacion: %s", self.ruta.name)

    @property
    def presentacion(self) -> Any:
        if self._presentacion is None:
            if Presentation is None:
                raise RuntimeError("python-pptx no esta disponible.")
            self._presentacion = Presentation()
        return self._presentacion

    def inspeccionar_diapositivas(self) -> list[dict[str, Any]]:
        """Inspecciona la totalidad de diapositivas, formas, textos, tablas y notas del orador."""
        if not self._presentacion:
            raise RuntimeError("No hay ninguna presentacion cargada en este cirujano.")

        informe_diapositivas: list[dict[str, Any]] = []

        for idx, slide in enumerate(self._presentacion.slides):
            formas_info: list[dict[str, Any]] = []

            for shape in slide.shapes:
                info_forma: dict[str, Any] = {
                    "id": shape.shape_id,
                    "nombre": shape.name,
                    "tipo": str(shape.shape_type),
                    "posicion": {
                        "izquierda_cm": round(shape.left / 360000, 2) if shape.left else 0,
                        "arriba_cm": round(shape.top / 360000, 2) if shape.top else 0,
                        "ancho_cm": round(shape.width / 360000, 2) if shape.width else 0,
                        "alto_cm": round(shape.height / 360000, 2) if shape.height else 0,
                    }
                }

                # Si tiene marco de texto
                if shape.has_text_frame:
                    parrafos_forma: list[dict[str, Any]] = []
                    for p in shape.text_frame.paragraphs:
                        runs_forma: list[dict[str, Any]] = []
                        for r in p.runs:
                            runs_forma.append({
                                "texto": r.text,
                                "negrita": r.font.bold,
                                "cursiva": r.font.italic,
                                "tamano_pt": r.font.size.pt if r.font.size else None,
                            })
                        parrafos_forma.append({
                            "texto": p.text,
                            "runs": runs_forma
                        })
                    info_forma["texto_completo"] = shape.text_frame.text
                    info_forma["parrafos"] = parrafos_forma

                # Si es una tabla
                if shape.has_table:
                    tabla_info: list[list[str]] = []
                    for row in shape.table.rows:
                        fila_texto = [cell.text.strip() for cell in row.cells]
                        tabla_info.append(fila_texto)
                    info_forma["tabla"] = tabla_info

                formas_info.append(info_forma)

            # Notas de orador
            notas_texto = ""
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                notas_texto = slide.notes_slide.notes_text_frame.text

            informe_diapositivas.append({
                "indice": idx + 1,
                "total_formas": len(formas_info),
                "formas": formas_info,
                "notas_orador": notas_texto
            })

        return informe_diapositivas

    def reemplazo_quirurgico_texto(
        self,
        texto_buscar: str,
        texto_reemplazo: str,
        ruta_salida: str | Path | None = None
    ) -> int:
        """Reemplaza texto quirurgicamente dentro de cualquier cuadro de texto o celda de tabla,
        preservando el formato de los runs intacto."""
        if not self._presentacion:
            raise RuntimeError("No hay ninguna presentacion cargada para reemplazo quirurgico.")

        total_reemplazos = 0

        for slide in self._presentacion.slides:
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for p in shape.text_frame.paragraphs:
                        for r in p.runs:
                            if texto_buscar in r.text:
                                r.text = r.text.replace(texto_buscar, texto_reemplazo)
                                total_reemplazos += 1
                                self._modificado = True

                if shape.has_table:
                    for row in shape.table.rows:
                        for cell in row.cells:
                            for p in cell.text_frame.paragraphs:
                                for r in p.runs:
                                    if texto_buscar in r.text:
                                        r.text = r.text.replace(texto_buscar, texto_reemplazo)
                                        total_reemplazos += 1
                                        self._modificado = True

        if total_reemplazos > 0:
            destino = Path(ruta_salida) if ruta_salida else self.ruta
            if destino:
                destino.parent.mkdir(parents=True, exist_ok=True)
                self._presentacion.save(str(destino))
                registro.info("Reemplazos realizados: %d. Guardado en: %s", total_reemplazos, destino)

        return total_reemplazos

    def inyectar_imagen_diapositiva(
        self,
        indice_diapositiva: int,
        ruta_imagen: str | Path,
        izquierda_cm: float,
        arriba_cm: float,
        ancho_cm: float | None = None,
        alto_cm: float | None = None,
        ruta_salida: str | Path | None = None
    ) -> bool:
        """Inyecta una imagen con coordenadas metricas precisas en una diapositiva especifica (base 1)."""
        if not self._presentacion:
            raise RuntimeError("No hay presentacion cargada.")

        img_path = Path(ruta_imagen)
        if not img_path.exists():
            raise FileNotFoundError(f"Imagen no encontrada: {img_path}")

        if indice_diapositiva < 1 or indice_diapositiva > len(self._presentacion.slides):
            raise IndexError(f"Indice de diapositiva {indice_diapositiva} fuera de rango (1..{len(self._presentacion.slides)})")

        slide = self._presentacion.slides[indice_diapositiva - 1]

        # 1 cm = 360000 EMUs
        left = int(izquierda_cm * 360000)
        top = int(arriba_cm * 360000)
        width = int(ancho_cm * 360000) if ancho_cm else None
        height = int(alto_cm * 360000) if alto_cm else None

        slide.shapes.add_picture(str(img_path), left, top, width=width, height=height)
        self._modificado = True

        destino = Path(ruta_salida) if ruta_salida else self.ruta
        if destino:
            destino.parent.mkdir(parents=True, exist_ok=True)
            self._presentacion.save(str(destino))
            registro.info("Imagen inyectada en diapositiva %d. Guardado en: %s", indice_diapositiva, destino)

        return True

    @classmethod
    def compilar_desde_svg(
        cls,
        archivos_svg: list[str | Path],
        ruta_salida_pptx: str | Path,
        formato_lienzo: str = "ppt169",
        formas_nativas: bool = True,
        transicion: str | None = "fade",
        notas: dict[str, str] | None = None
    ) -> bool:
        """Compila un conjunto de diapositivas SVG a una presentacion PPTX nativa DrawingML usando PPT-Master."""
        if not create_pptx_with_native_svg:
            raise RuntimeError("El modulo svg_to_pptx de PPT-Master no esta disponible.")

        rutas_svg = [Path(p) for p in archivos_svg]
        for f in rutas_svg:
            if not f.exists():
                raise FileNotFoundError(f"Archivo SVG no encontrado: {f}")

        destino = Path(ruta_salida_pptx)
        destino.parent.mkdir(parents=True, exist_ok=True)

        return create_pptx_with_native_svg(
            svg_files=rutas_svg,
            output_path=destino,
            canvas_format=formato_lienzo,
            use_native_shapes=formas_nativas,
            notes=notas,
            transition=transicion,
            verbose=False
        )

    @classmethod
    def renderizar_formula_latex(
        cls,
        formula_latex: str,
        ruta_salida_png: str | Path,
        dpi: int = 300,
        color_hex: str = "000000",
        fondo_hex: str = "FFFFFF",
        display: str = "block",
        hacer_transparente: bool = True,
        tolerancia_transparencia: int = 12
    ) -> dict[str, Any]:
        """Renderiza una expresion matematica en formato LaTeX a una imagen PNG de 300 DPI con fondo transparente."""
        if not latex_render:
            raise RuntimeError("El motor latex_render de PPT-Master no esta disponible.")

        salida = Path(ruta_salida_png)
        salida.parent.mkdir(parents=True, exist_ok=True)

        proveedores = ["codecogs", "quicklatex", "mathpad", "wikimedia"]
        color_limpio = color_hex.lstrip("#")
        fondo_limpio = fondo_hex.lstrip("#")

        proveedor_exitoso, errores = latex_render._render_with_providers(
            latex=formula_latex,
            output_path=salida,
            dpi=dpi,
            color=color_limpio,
            background=fondo_limpio,
            display=display,
            providers=proveedores
        )

        if hacer_transparente:
            latex_render._make_png_background_transparent(
                salida,
                color=color_limpio,
                background=fondo_limpio,
                tolerance=tolerancia_transparencia
            )

        dimensiones = latex_render._image_dimensions(salida)
        return {
            "exito": True,
            "proveedor": proveedor_exitoso,
            "ruta": str(salida),
            "ancho_px": dimensiones[0],
            "alto_px": dimensiones[1],
            "tamano_bytes": salida.stat().st_size
        }

    @classmethod
    def extraer_a_markdown(
        cls,
        ruta_pptx: str | Path,
        ruta_salida_md: str | Path | None = None
    ) -> str:
        """Extrae el contenido de una presentacion PPTX a Markdown enriquecido con tablas y notas de orador."""
        if not convert_presentation_to_markdown:
            raise RuntimeError("El modulo ppt_to_md de PPT-Master no esta disponible.")

        origen = Path(ruta_pptx)
        if not origen.exists():
            raise FileNotFoundError(f"Archivo PPTX no encontrado: {origen}")

        destino = Path(ruta_salida_md) if ruta_salida_md else origen.with_suffix(".md")
        destino.parent.mkdir(parents=True, exist_ok=True)

        resultado = convert_presentation_to_markdown(str(origen), str(destino))
        if not resultado and destino.exists():
            return destino.read_text(encoding="utf-8")
        return resultado or ""

    @classmethod
    def convertir_a_svg(
        cls,
        ruta_pptx: str | Path,
        directorio_salida: str | Path
    ) -> dict[str, Any]:
        """Convierte una presentacion PPTX en una coleccion de archivos SVG individuales."""
        if not convert_pptx_to_svg:
            raise RuntimeError("El modulo pptx_to_svg de PPT-Master no esta disponible.")

        origen = Path(ruta_pptx)
        if not origen.exists():
            raise FileNotFoundError(f"Archivo PPTX no encontrado: {origen}")

        destino = Path(directorio_salida)
        destino.mkdir(parents=True, exist_ok=True)

        convert_pptx_to_svg(origen, destino)

        archivos_generados = [str(f) for f in destino.rglob("*.svg")]
        return {
            "exito": True,
            "directorio_salida": str(destino),
            "total_svgs": len(archivos_generados),
            "archivos": archivos_generados
        }
