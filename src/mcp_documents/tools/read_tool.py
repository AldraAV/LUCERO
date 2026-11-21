from pathlib import Path
from typing import Any

import aiofiles
import structlog
from docx import Document
from pypdf import PdfReader

from ..core.tools import Tool

log = structlog.get_logger()

class ReadTool(Tool):
    def __init__(self):
        super().__init__(
            name="read_document",
            description="Read any document (DOCX, PDF, MD, TXT) and extract content"
        )
    
    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        file_path = params.get("file_path")
        extract_type = params.get("extract_type", "full_text")
        start_line = params.get("start_line")
        end_line = params.get("end_line")
        search_query = params.get("search_query")
        outline_only = bool(params.get("outline_only", False))
        offset = int(params.get("offset", 0) or 0)
        limit = int(params.get("limit", 8000) or 8000)

        try:
            path = Path(file_path)
            suffix = path.suffix.lower()

            if outline_only:
                from ...navegador_documentos import obtener_esquema_documento

                esquema = obtener_esquema_documento(file_path)
                return {"success": True, "data": esquema}

            if search_query:
                from ...navegador_documentos import buscar_en_documento

                busqueda = buscar_en_documento(file_path, consulta=search_query)
                return {"success": True, "data": busqueda}

            if start_line is not None or end_line is not None:
                from ...navegador_documentos import leer_rango_documento

                rango = leer_rango_documento(
                    file_path,
                    linea_inicio=int(start_line) if start_line is not None else None,
                    linea_fin=int(end_line) if end_line is not None else None,
                )
                return {"success": True, "data": rango}

            if suffix == ".docx":
                content = await self._read_docx(file_path, extract_type)
            elif suffix == ".pdf":
                content = await self._read_pdf(file_path, extract_type)
            elif suffix == ".pptx":
                content = await self._read_pptx(file_path, extract_type)
            elif suffix in [".md", ".txt"]:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
            else:
                return {
                    "success": False,
                    "error": f"Unsupported format: {suffix}"
                }

            total_chars = len(content)
            if offset > 0 or total_chars > limit:
                content_slice = content[offset : offset + limit]
                hay_mas = (offset + limit) < total_chars
                return {
                    "success": True,
                    "data": {
                        "format": suffix,
                        "path": str(path),
                        "content": content_slice,
                        "offset": offset,
                        "limit": limit,
                        "total_chars": total_chars,
                        "has_more": hay_mas,
                        "next_offset": (offset + limit) if hay_mas else None,
                    }
                }

            return {
                "success": True,
                "data": {
                    "format": suffix,
                    "path": str(path),
                    "content": content,
                    "size_bytes": path.stat().st_size,
                    "encoding": "utf-8"
                }
            }
        
        except Exception as e:
            log.error("read_error", error=str(e), file_path=file_path)
            return {"success": False, "error": str(e)}
    
    async def _read_docx(self, file_path: str, extract_type: str) -> str:
        """Extract DOCX content with python-docx."""
        doc = Document(file_path)
        
        if extract_type == "full_text":
            return "\n".join([p.text for p in doc.paragraphs])
        
        elif extract_type == "tables":
            tables_text = []
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join([cell.text for cell in row.cells])
                    tables_text.append(row_text)
            return "\n".join(tables_text)
        
        elif extract_type == "metadata":
            core_props = doc.core_properties
            return f"Title: {core_props.title}\nAuthor: {core_props.author}\nCreated: {core_props.created}"
        
        else:
            full = "\n".join([p.text for p in doc.paragraphs])
            return full
    
    async def _read_pdf(self, file_path: str, extract_type: str) -> str:
        """Extract PDF content with pypdf."""
        reader = PdfReader(file_path)
        
        if extract_type == "full_text":
            text = []
            for page in reader.pages:
                text.append(page.extract_text())
            return "\n".join(text)
        elif extract_type == "metadata":
            meta = reader.metadata
            return f"Title: {meta.get('/Title', 'N/A')}\nAuthor: {meta.get('/Author', 'N/A')}"
        else:
            return await self._read_pdf(file_path, "full_text")

    async def _read_pptx(self, file_path: str, extract_type: str) -> str:
        """Extrae el contenido de un archivo PPTX utilizando PptxSurgeon y python-pptx."""
        from ...pptx_surgeon import PptxSurgeon
        import json as _json
        cirujano = PptxSurgeon(file_path)
        if extract_type == "metadata" or extract_type == "all":
            diapositivas = cirujano.inspeccionar_diapositivas()
            return _json.dumps(diapositivas, ensure_ascii=False, indent=2)
        try:
            texto_md = PptxSurgeon.extraer_a_markdown(file_path)
            if texto_md:
                return texto_md
        except Exception:
            pass
        diapositivas = cirujano.inspeccionar_diapositivas()
        bloques: list[str] = []
        for diap in diapositivas:
            lineas = [f"=== Diapositiva {diap['indice']} ==="]
            for forma in diap.get("formas", []):
                if "texto_completo" in forma and forma["texto_completo"].strip():
                    lineas.append(f"[{forma['nombre']}] ({forma['posicion']['izquierda_cm']}cm, {forma['posicion']['arriba_cm']}cm): {forma['texto_completo']}")
                if "tabla" in forma:
                    for fila in forma["tabla"]:
                        lineas.append(" | ".join(fila))
            if diap.get("notas_orador"):
                lineas.append(f"Notas: {diap['notas_orador']}")
            bloques.append("\n".join(lineas))
        return "\n\n".join(bloques)

    def _mcp_schema(self):
        return {
            "name": "read_document",
            "description": "Read and extract content from documents",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to file"},
                    "extract_type": {
                        "type": "string",
                        "enum": ["full_text", "metadata", "tables", "images", "all"],
                        "default": "full_text"
                    }
                },
                "required": ["file_path"]
            }
        }
