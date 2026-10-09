from pathlib import Path
from typing import Any

import structlog

from ..core.tools import Tool

log = structlog.get_logger()

class MarkitdownTool(Tool):
    def __init__(self):
        super().__init__(
            name="analizar_documento_markitdown",
            description="Convierte documentos complejos (PDF, PPTX, XLSX, Word, ZIP, Audio) a Markdown nativo utilizando Microsoft MarkItDown. Extrae texto, tablas y metadata."
        )

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        file_path = params.get("file_path")
        
        if not file_path:
            return {"success": False, "error": "El parámetro 'file_path' es requerido."}
            
        target_file = Path(file_path)
        if not target_file.exists():
            return {"success": False, "error": f"El archivo '{file_path}' no existe."}

        try:
            from markitdown import MarkItDown
            
            log.info("markitdown.iniciando_conversion", file=str(target_file))
            
            # Instanciar MarkItDown. Si detecta variables de entorno para OpenAI, activará LLM Vision.
            # En el Aldraverse, si se quiere extraer info de imágenes con LLM, se podría configurar.
            # Por ahora, usamos la versión estándar offline a menos que se configure OPENAI_API_KEY.
            
            md_client = MarkItDown()
            
            # Si el usuario quiere OCR y tiene llave de OpenAI:
            # from openai import OpenAI
            # client = OpenAI()
            # md_client = MarkItDown(llm_client=client, llm_model="gpt-4o")

            # La conversión es síncrona en MarkItDown, pero como esto está en un servidor async,
            # podríamos envolverlo si fuera muy pesado. Por ahora lo dejamos directo.
            result = md_client.convert(str(target_file))
            
            return {
                "success": True,
                "data": {
                    "markdown_content": result.text_content,
                    "credits": "Powered by Microsoft MarkItDown"
                }
            }
            
        except Exception as e:
            log.error("markitdown_error", error=str(e), file=str(target_file))
            return {"success": False, "error": f"Error al procesar el archivo: {e!s}"}
