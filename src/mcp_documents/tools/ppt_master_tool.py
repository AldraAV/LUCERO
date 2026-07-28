import os
import re
import asyncio
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any
import structlog
from ..core.tools import Tool

log = structlog.get_logger()

class PptMasterTool(Tool):
    def __init__(self):
        super().__init__(
            name="generar_presentacion_elite",
            description="Genera una presentación nativa de alta calidad (.pptx) usando el orquestador ppt-master con estética del Aldraverse."
        )
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        content = params.get("content")
        if not content:
            return {"success": False, "error": "El parámetro 'content' es requerido."}
            
        topic = params.get("topic", "Presentación")
        num_slides = params.get("num_slides", 5)
        
        # Obtener API Key del entorno (Aldraverse standard)
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return {"success": False, "error": "GEMINI_API_KEY no configurado en el entorno de LUCERO."}
            
        try:
            # Crear directorio temporal para el proyecto ppt-master
            temp_dir = tempfile.mkdtemp(prefix="ppt_master_")
            svg_out_dir = Path(temp_dir) / "svg_output"
            svg_out_dir.mkdir(exist_ok=True)
            
            # 1. Llamar a Gemini para generar los SVGs
            log.info("ppt_master.generando_svgs", num_slides=num_slides)
            svgs_generados = await self._generar_svgs_gemini(api_key, topic, content, num_slides)
            
            if not svgs_generados:
                return {"success": False, "error": "Gemini no generó ningún código SVG válido."}
                
            # 2. Guardar los SVGs en svg_output
            for i, svg_content in enumerate(svgs_generados):
                page_num = str(i + 1).zfill(2)
                file_path = svg_out_dir / f"page_{page_num}.svg"
                file_path.write_text(svg_content, encoding="utf-8")
                
            # 3. Compilar con svg_to_pptx.py de ppt-master
            output_pptx = Path(temp_dir) / f"{topic.replace(' ', '_')}.pptx"
            
            # Asumimos que ppt_master_integration está en la raíz de LUCERO
            lucero_root = Path(__file__).parent.parent.parent.parent
            svg_to_pptx_script = lucero_root / "ppt_master_integration" / "skills" / "ppt-master" / "scripts" / "svg_to_pptx.py"
            
            if not svg_to_pptx_script.exists():
                return {"success": False, "error": f"No se encontró svg_to_pptx.py en {svg_to_pptx_script}"}
                
            cmd = [
                "python", str(svg_to_pptx_script),
                "--input", str(temp_dir),
                "--output", str(output_pptx)
            ]
            
            log.info("ppt_master.compilando_pptx", cmd=" ".join(cmd))
            
            # Ejecutar de forma asíncrona
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                log.error("ppt_master.error_compilacion", stderr=stderr.decode())
                return {"success": False, "error": f"Error al compilar PPTX: {stderr.decode()}"}
                
            # Mover a una ruta accesible
            final_path = lucero_root / f"presentacion_elite_{topic.replace(' ', '_')}.pptx"
            import shutil
            shutil.copy(str(output_pptx), str(final_path))
            
            return {
                "success": True,
                "data": {
                    "output_path": str(final_path),
                    "slides_generated": len(svgs_generados),
                    "credits": "Powered by ppt-master (Hugohe3) & Gemini 3.1"
                }
            }
            
        except Exception as e:
            log.error("ppt_master_error", error=str(e))
            return {"success": False, "error": str(e)}

    async def _generar_svgs_gemini(self, api_key: str, topic: str, content: str, num_slides: int):
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=api_key)
        
        system_prompt = f"""
Eres un diseñador experto (ppt-master Strategist & Executor) del 'Aldraverse'. 
Tu objetivo es transformar el contenido proporcionado en {num_slides} páginas de presentación, devolviendo EXCLUSIVAMENTE código SVG para cada diapositiva.

### REGLAS INAPELABLES DEL ALDRAVERSE:
1. **Idioma Estricto**: Todo el texto debe estar en Español Latino.
2. **Tipografías**: 
   - Títulos y encabezados: `Space Grotesk`
   - Texto base y descripciones: `Inter`
   - Acentos / Botones: `Poppins`
3. **Colores (Aurora Visual Aesthetics)**:
   - Usa un esquema de Glassmorphism / translúcido.
   - Colores principales: Lava Neon (naranja brillante/rojo), Cherry (Rojo cereza profundo), Amber Sunlight (Amarillo ámbar).
   - Fondos: Oscuros o sutiles para resaltar el neón.
4. **Dimensiones**: Cada SVG debe ser `<svg width="1920" height="1080" viewBox="0 0 1920 1080" xmlns="http://www.w3.org/2000/svg">`
5. **Formato de Respuesta**: 
   Debes devolver CADA diapositiva envuelta en etiquetas:
   ```xml
   <slide>
   <svg width="1920" height="1080" ...>
   ...
   </svg>
   </slide>
   ```
   Genera exactamente {num_slides} bloques <slide>. NO incluyas explicaciones, solo XML.
"""

        user_prompt = f"Tema: {topic}\n\nContenido base:\n{content}"
        
        # We will use the standard model available in the environment (e.g. gemini-2.0-flash or gemini-1.5-pro)
        model_id = "gemini-2.5-pro" # fallback to highest available, or gemini-2.0-flash
        
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.5-pro", # This will be routed by google-genai
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.3
                )
            )
            response_text = response.text
        except Exception as e:
            # Fallback a gemini-2.0-flash si 2.5-pro no está disponible
            log.warning("ppt_master.fallback_model", error=str(e))
            response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.0-flash",
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.3
                )
            )
            response_text = response.text

        # Extraer los SVGs
        svgs = re.findall(r'<svg.*?</svg>', response_text, re.DOTALL)
        return svgs
