"""
Módulo Oficial de Humanización Masiva para LUCERO.
Desarrollado estrictamente en español siguiendo la ley soberana del Aldraverso.
"""
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

from .surgeon import DocxSurgeon
from .utils import NS, get_logger

logger = get_logger("HumanizadorMasivo")

def obtener_clave_gemini() -> str:
    """Busca y recupera la llave de API de Gemini desde las variables de entorno o archivo .env"""
    rutas = [
        Path(r"C:\Users\carde\Desktop\MUACK_2.0\LUCERO\.env"),
        Path(r"C:\Users\carde\.gemini\antigravity\mcp\LUCERO\.env"),
        Path(r"C:\Users\carde\Desktop\MUACK_2.0\.env")
    ]
    for ruta in rutas:
        if ruta.exists():
            load_dotenv(ruta)
            
    return os.getenv("GEMINI_API_KEY", "")

def llamar_llm_humanizador(texto: str, clave_api: str) -> str:
    """Invoca la API REST de Gemini para aplicar la skill de humanización a un fragmento de texto."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={clave_api}"
    cabeceras = {"Content-Type": "application/json"}
    
    instruccion = (
        "Actúa como un redactor profesional experto. "
        "Reescribe el siguiente texto para que suene natural, directo y humano. "
        "Elimina las muletillas, frases rimbombantes y el tono 'robótico' típico de la IA, "
        "pero CONSERVA la relevancia, los datos duros y el mensaje original exacto. "
        "Devuelve ÚNICAMENTE el texto humanizado, sin introducciones, sin comentarios, sin markdown de bloques de código y sin comillas.\n\n"
        f"Texto original:\n{texto}"
    )
    
    datos = {
        "contents": [{"parts": [{"text": instruccion}]}],
        "generationConfig": {"temperature": 0.3}
    }
    
    try:
        respuesta = requests.post(url, headers=cabeceras, json=datos, timeout=20)
        time.sleep(4.1) # Protección contra límite de peticiones (15 RPM en tier gratuito)
        if respuesta.status_code == 200:
            json_resp = respuesta.json()
            try:
                texto_generado = json_resp["candidates"][0]["content"]["parts"][0]["text"]
                return texto_generado.strip()
            except (KeyError, IndexError):
                return texto
        else:
            logger.warning(f"Error en API de Gemini: {respuesta.status_code}")
            return texto
    except Exception as e:
        logger.error(f"Fallo de conexión: {e}")
        return texto

def humanizar_documento_completo(ruta_docx: str) -> None:
    """
    Función principal que barre el documento, aísla los párrafos que no son títulos
    y procesa el texto en masa mediante la API de Gemini.
    """
    clave_api = obtener_clave_gemini()
    if not clave_api:
        logger.error("Operación abortada: No se encontró GEMINI_API_KEY en el entorno soberano.")
        return
        
    cirujano = DocxSurgeon(ruta_docx)
    nodos_parrafo = cirujano.find_by_xpath('//w:p')
    logger.info(f"Análisis inicial: Se detectaron {len(nodos_parrafo)} párrafos en la estructura XML.")
    
    parrafos_modificados = 0
    
    for parrafo in nodos_parrafo:
        # Verificar estilos para saltar títulos, subtítulos, índices y tablas de contenido
        estilos = parrafo.xpath('.//w:pStyle/@w:val', namespaces=NS)
        es_excluido = False
        if estilos:
            val_estilo = estilos[0].lower()
            palabras_excluidas = ["heading", "title", "ttulo", "toc", "caption", "list", "index"]
            if any(palabra in val_estilo for palabra in palabras_excluidas):
                es_excluido = True
                
        if es_excluido:
            continue
            
        nodos_texto = parrafo.xpath('.//w:t', namespaces=NS)
        if not nodos_texto:
            continue
            
        texto_completo = "".join([t.text for t in nodos_texto if t.text])
        
        # Ignorar párrafos demasiado cortos o vacíos (ej. retornos de carro, enumeraciones sueltas)
        if len(texto_completo.strip()) < 60:
            continue
            
        # Llamar a la API
        texto_humanizado = llamar_llm_humanizador(texto_completo, clave_api)
        
        if texto_humanizado and texto_humanizado != texto_completo:
            # Concentrar el texto humanizado en el primer nodo de texto y limpiar los demás
            # Esto sacrifica los estilos en línea (negritas parciales) a favor de la coherencia del bloque.
            for indice, nodo_t in enumerate(nodos_texto):
                if indice == 0:
                    nodo_t.text = texto_humanizado
                else:
                    nodo_t.text = ""
            parrafos_modificados += 1
            cirujano._dirty = True
            
    if parrafos_modificados > 0:
        cirujano.commit_changes()
        logger.info(f"Auditoría y parcheo completados. Se humanizaron {parrafos_modificados} párrafos con éxito.")
    else:
        logger.info("El análisis concluyó sin encontrar párrafos candidatos o sin modificaciones necesarias.")
