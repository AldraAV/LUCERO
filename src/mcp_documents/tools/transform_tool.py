import asyncio
import subprocess
from pathlib import Path
from typing import Any

import structlog

from ..core.tools import Tool

log = structlog.get_logger()

class TransformTool(Tool):
    def __init__(self):
        super().__init__(
            name="transform_document",
            description="Convert between formats (DOCX↔PDF↔Markdown)"
        )
    
    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        source_path = params.get("source_path")
        target_format = params.get("target_format")
        
        try:
            output_path = params.get("output_path")
            source = Path(source_path)
            target_path = Path(output_path) if output_path else source.with_suffix(f".{target_format}")
            source_fmt = source.suffix.lower()
            
            if source_fmt == ".docx" and target_format == "pdf":
                await self._docx_to_pdf(source_path, str(target_path))
            elif target_format in ("md", "markdown"):
                await self._to_markdown(source_path, str(target_path))
            else:
                return {
                    "success": False,
                    "error": f"Conversion {source_fmt} -> {target_format} no soportada"
                }
            
            datos_respuesta = {
                "source": str(source),
                "target": str(target_path),
                "format": target_format,
                "size_bytes": target_path.stat().st_size,
                "motor": "Microsoft MarkItDown" if target_format in ("md", "markdown") else "LibreOffice"
            }
            if target_format in ("md", "markdown") and target_path.exists():
                with open(target_path, "r", encoding="utf-8") as f:
                    contenido_md = f.read()
                datos_respuesta["resumen"] = contenido_md[:400]
                datos_respuesta["longitud_caracteres"] = len(contenido_md)

            return {
                "success": True,
                "data": datos_respuesta
            }
        
        except Exception as e:
            log.error("transform_error", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def _docx_to_pdf(self, docx_path: str, pdf_path: str):
        cmd = [
            "libreoffice",
            "--headless",
            "--convert-to", "pdf",
            "--outdir", str(Path(pdf_path).parent),
            docx_path
        ]
        await asyncio.to_thread(subprocess.run, cmd, check=True)
    
    async def _to_markdown(self, source_path: str, md_path: str):
        try:
            from markitdown import MarkItDown
            cliente_markitdown = MarkItDown()
            resultado = await asyncio.to_thread(cliente_markitdown.convert, source_path)
            with open(md_path, "w", encoding="utf-8") as archivo:
                archivo.write(resultado.text_content)
            log.info("markitdown_conversion_exitosa", origen=source_path, destino=md_path)
        except Exception as error_markitdown:
            log.warning("markitdown_fallo_intentando_pandoc", error=str(error_markitdown))
            cmd = ["pandoc", source_path, "-o", md_path]
            await asyncio.to_thread(subprocess.run, cmd, check=True)

