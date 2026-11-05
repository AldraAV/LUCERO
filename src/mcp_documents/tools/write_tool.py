from pathlib import Path
from typing import Any

import aiofiles
import structlog
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

from ..core.tools import Tool
from ..integrations.encryption import AES256Crypto

log = structlog.get_logger()

class WriteTool(Tool):
    def __init__(self):
        super().__init__(
            name="write_document",
            description="Write/modify documents with full formatting support (APA 7th edition)"
        )
        self.crypto = AES256Crypto()
    
    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        file_path = params.get("file_path")
        content = params.get("content")
        format = params.get("format", "docx")
        append = params.get("append", False)
        encrypt = params.get("encrypt", False)
        password = params.get("password", "")
        
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            if format == "docx":
                await self._write_docx(file_path, content, append)
            elif format == "md" or format == "txt":
                mode = "a" if append else "w"
                async with aiofiles.open(file_path, mode, encoding="utf-8") as f:
                    await f.write(content)
            else:
                return {"success": False, "error": f"Unsupported format: {format}"}
            
            if not path.exists():
                return {
                    "success": False, 
                    "error": f"Archivo no se creó en {file_path}",
                    "debug": {"attempted_path": file_path}
                }
            
            file_size = path.stat().st_size
            if file_size == 0:
                return {
                    "success": False, 
                    "error": "Archivo creado pero vacío (0 bytes)"
                }
            
            if encrypt and password:
                encrypted_path = await self.crypto.encrypt_file(file_path, password)
                return {
                    "success": True,
                    "data": {
                        "path": encrypted_path,
                        "encrypted": True,
                        "original_size": path.stat().st_size
                    }
                }
            
            return {
                "success": True,
                "data": {
                    "path": str(path),
                    "format": format,
                    "size_bytes": path.stat().st_size
                }
            }
        
        except Exception as e:
            log.error("write_error", error=str(e), file_path=file_path)
            return {"success": False, "error": str(e)}
    
    async def _write_docx(self, file_path: str, content: str, append: bool):
        if append and Path(file_path).exists():
            doc = Document(file_path)
        else:
            doc = Document()
            # Configurar márgenes de 1 pulgada (2.54 cm) para APA 7
            for section in doc.sections:
                section.top_margin = Inches(1)
                section.bottom_margin = Inches(1)
                section.left_margin = Inches(1)
                section.right_margin = Inches(1)
                
                # Número de página en el encabezado alineado a la derecha
                header = section.header
                hp = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
                hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                hrun = hp.add_run()
                hrun.font.name = 'Times New Roman'
                hrun.font.size = Pt(12)
                fldSimple = parse_xml(r'<w:fldSimple %s w:instr="PAGE"/>' % nsdecls('w'))
                hrun._r.append(fldSimple)

            # Estilo Normal base APA 7
            estilo_normal = doc.styles['Normal']
            estilo_normal.font.name = 'Times New Roman'
            estilo_normal.font.size = Pt(12)
            estilo_normal.font.color.rgb = RGBColor(0, 0, 0)
        
        for paragraph_text in content.split("\n\n"):
            p_limpio = paragraph_text.strip()
            if not p_limpio:
                continue

            # Mapeo de niveles APA 7 estricto
            if p_limpio.startswith("# "):
                # Nivel 1: Centrado, Negrita, Times New Roman 12pt
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.line_spacing = 2.0
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                r = p.add_run(p_limpio[2:].strip())
                r.bold = True
                r.font.name = 'Times New Roman'
                r.font.size = Pt(12)
                r.font.color.rgb = RGBColor(0, 0, 0)

            elif p_limpio.startswith("## "):
                # Nivel 2: Izquierda, Negrita, Times New Roman 12pt
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.line_spacing = 2.0
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                r = p.add_run(p_limpio[3:].strip())
                r.bold = True
                r.font.name = 'Times New Roman'
                r.font.size = Pt(12)
                r.font.color.rgb = RGBColor(0, 0, 0)

            elif p_limpio.startswith("### "):
                # Nivel 3: Izquierda, Negrita, Cursiva, Times New Roman 12pt
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.line_spacing = 2.0
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                r = p.add_run(p_limpio[4:].strip())
                r.bold = True
                r.italic = True
                r.font.name = 'Times New Roman'
                r.font.size = Pt(12)
                r.font.color.rgb = RGBColor(0, 0, 0)

            elif p_limpio.startswith("#### "):
                # Nivel 4: Sangría 0.5", Negrita, punto final
                txt = p_limpio[5:].strip()
                if not txt.endswith("."):
                    txt += "."
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.first_line_indent = Inches(0.5)
                p.paragraph_format.line_spacing = 2.0
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                r = p.add_run(txt)
                r.bold = True
                r.font.name = 'Times New Roman'
                r.font.size = Pt(12)
                r.font.color.rgb = RGBColor(0, 0, 0)

            elif p_limpio.startswith("##### "):
                # Nivel 5: Sangría 0.5", Negrita, Cursiva, punto final
                txt = p_limpio[6:].strip()
                if not txt.endswith("."):
                    txt += "."
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.first_line_indent = Inches(0.5)
                p.paragraph_format.line_spacing = 2.0
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                r = p.add_run(txt)
                r.bold = True
                r.italic = True
                r.font.name = 'Times New Roman'
                r.font.size = Pt(12)
                r.font.color.rgb = RGBColor(0, 0, 0)

            else:
                # Párrafo Normal APA 7: Sangría 0.5", Interlineado Doble
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.first_line_indent = Inches(0.5)
                p.paragraph_format.line_spacing = 2.0
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                r = p.add_run(paragraph_text)
                r.font.name = 'Times New Roman'
                r.font.size = Pt(12)
                r.font.color.rgb = RGBColor(0, 0, 0)
        
        doc.save(file_path)
