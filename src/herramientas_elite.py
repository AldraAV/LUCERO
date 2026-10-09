"""
herramientas_elite.py — Módulo de procesamiento inteligente y análisis
de documentos de nivel Élite (Tiers 1-5).
"""

import json
import os
from pathlib import Path
from typing import Any

import httpx

from .mcp_documents.tools.read_tool import ReadTool
from .utils import get_logger

log = get_logger("lucero.herramientas_elite")

# ─── Carga de variables de entorno manual ──────────────────
def cargar_env():
    """Busca y carga las variables de entorno desde el .env del proyecto."""
    for directorio_actual in (Path(__file__).parent.parent, Path(__file__).parent.parent.parent):
        env_path = directorio_actual / ".env"
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for linea in f:
                    linea = linea.strip()
                    if linea and not linea.startswith("#") and "=" in linea:
                        clave, valor = linea.split("=", 1)
                        os.environ[clave.strip()] = valor.strip()
            log.info("Variables de entorno cargadas.")

# Llamar a cargar_env al iniciar el módulo
cargar_env()

async def consultar_gemini(prompt_sistema: str, prompt_usuario: str, max_tokens: int = 3000, temperature: float = 0.2) -> str:
    """Realiza una consulta a la API de Gemini usando gemini-2.5-flash."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Falta GEMINI_API_KEY en las variables de entorno de LUCERO.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    cabeceras = {
        "Content-Type": "application/json"
    }
    cuerpo = {
        "systemInstruction": {
            "parts": [
                {
                    "text": prompt_sistema
                }
            ]
        },
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": prompt_usuario
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens
        }
    }

    async with httpx.AsyncClient() as cliente:
        respuesta = await cliente.post(
            url,
            headers=cabeceras,
            json=cuerpo,
            timeout=90.0
        )
        respuesta.raise_for_status()
        resultado = respuesta.json()
        
        try:
            return resultado["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise ValueError(f"Formato de respuesta inesperado de Gemini API: {e}. Respuesta cruda: {resultado}")


async def consultar_groq(prompt_sistema: str, prompt_usuario: str, max_tokens: int = 3000, temperature: float = 0.2) -> str:
    """Realiza una consulta a la API de Groq usando LLaMA 3.3 70B."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("Falta GROQ_API_KEY en las variables de entorno de LUCERO.")

    cabeceras = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    cuerpo = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    async with httpx.AsyncClient() as cliente:
        respuesta = await cliente.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=cabeceras,
            json=cuerpo,
            timeout=90.0
        )
        respuesta.raise_for_status()
        resultado = respuesta.json()
        return resultado["choices"][0]["message"]["content"]


async def consultar_llm(
    prompt_sistema: str,
    prompt_usuario: str,
    max_tokens: int = 3000,
    temperature: float = 0.2,
    ctx: Any | None = None
) -> str:
    """Consulta a un LLM: intenta Gemini, luego Groq, y finalmente Sampling si hay contexto de MCP."""
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            log.info("Consultando Gemini API...")
            return await consultar_gemini(prompt_sistema, prompt_usuario, max_tokens, temperature)
        except Exception as e:
            log.warning("Fallo en Gemini API: %s. Intentando con Groq si está disponible.", e)

    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            log.info("Consultando Groq API...")
            return await consultar_groq(prompt_sistema, prompt_usuario, max_tokens, temperature)
        except Exception as e:
            log.warning("Fallo en Groq API: %s. Reintentando con sampling si está disponible.", e)

    if ctx and hasattr(ctx, "session") and ctx.session:
        log.info("Usando Sampling en el cliente MCP.")
        try:
            from mcp import types
            # Mensajes de muestreo
            mensajes = [
                types.SamplingMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"Prompt de Sistema:\n{prompt_sistema}\n\nDatos de entrada:\n{prompt_usuario}"
                    )
                )
            ]
            if hasattr(ctx.session, "create_message"):
                res = await ctx.session.create_message(
                    messages=mensajes,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system_prompt="Sigue detalladamente las instrucciones y restricciones del Prompt de Sistema."
                )
                if res and res.content:
                    if isinstance(res.content, list):
                        return res.content[0].text
                    return res.content.text
            else:
                from mcp.types import CreateMessageRequestParams
                params = CreateMessageRequestParams(
                    messages=mensajes,
                    maxTokens=max_tokens,
                    temperature=temperature,
                    systemPrompt="Sigue detalladamente las instrucciones y restricciones del Prompt de Sistema."
                )
                res = await ctx.session.send_request(
                    types.Request(
                        method="sampling/createMessage",
                        params=params
                    )
                )
                if res and hasattr(res, "content") and res.content:
                    if isinstance(res.content, list):
                        return res.content[0].text
                    return res.content.text
        except Exception as e:
            log.error("Fallo crítico en Sampling MCP: %s", e, exc_info=True)
            raise ValueError(f"Fallo al invocar Sampling en el agente: {e}")

    raise ValueError("Falta GEMINI_API_KEY o GROQ_API_KEY en variables de entorno y no hay Contexto de Sampling activo.")


async def leer_texto_documento(ruta_archivo: str) -> str:
    """Lee el texto completo de un documento usando la herramienta de lectura interna."""
    lector = ReadTool()
    resultado = await lector.execute({"file_path": ruta_archivo, "extract_type": "full_text"})
    if not resultado.get("success"):
        raise ValueError(f"Fallo al leer el documento: {resultado.get('error')}")
    return resultado["data"]["content"]


# ─────────────────────────────────────────────────────────────────────────────
# TIER 1: ANÁLISIS INTELIGENTE
# ─────────────────────────────────────────────────────────────────────────────

async def comparar_documentos_impl(rutas_documentos: list[str], ctx: Any | None = None) -> dict[str, Any]:
    """Compara múltiples documentos para identificar conflictos, consistencias y vacíos."""
    textos = []
    for ruta in rutas_documentos:
        nombre = Path(ruta).name
        contenido = await leer_texto_documento(ruta)
        # Truncar si es excesivo para la ventana de contexto
        textos.append(f"--- DOCUMENTO: {nombre} ---\n{contenido[:12000]}")

    contexto_documentos = "\n\n".join(textos)
    
    prompt_sistema = (
        "Eres un analista de documentos élite. Compara detalladamente los documentos provistos. "
        "Debes responder estrictamente en formato JSON válido con las siguientes claves: "
        "'consistencias' (lista de puntos en los que todos los documentos concuerdan), "
        "'conflictos' (lista de contradicciones o discrepancias detalladas con referencias a los nombres de archivos), "
        "'gaps' (vacíos de información importantes identificados entre ellos). "
        "No incluyas texto explicativo fuera del JSON."
    )
    
    prompt_usuario = f"Compara estos documentos:\n\n{contexto_documentos}"
    
    respuesta = await consultar_llm(prompt_sistema, prompt_usuario, ctx=ctx)
    try:
        # Limpiar posibles formatos markdown
        if respuesta.strip().startswith("```json"):
            respuesta = respuesta.strip().split("```json")[1].split("```")[0].strip()
        elif respuesta.strip().startswith("```"):
            respuesta = respuesta.strip().split("```")[1].split("```")[0].strip()
        return json.loads(respuesta)
    except Exception:
        return {
            "error": "No se pudo parsear la respuesta del LLM como JSON.",
            "respuesta_cruda": respuesta
        }


async def extraer_selectivo_impl(ruta_documento: str, tipo_extraccion: str, ctx: Any | None = None) -> dict[str, Any]:
    """Extrae selectivamente elementos específicos (dates, tables, metadata, names, custom)."""
    contenido = await leer_texto_documento(ruta_documento)
    
    prompts_tipo = {
        "dates": "Extrae todas las fechas clave, hitos y fechas límite mencionadas en el documento.",
        "tables": "Extrae de forma estructurada todas las tablas o datos tabulares que encuentres.",
        "metadata": "Extrae metadatos del documento como títulos, autores, fechas de creación, versión o firmantes.",
        "names": "Extrae todos los nombres de personas, cargos, organizaciones y entidades mencionadas."
    }
    
    instruccion = prompts_tipo.get(tipo_extraccion, f"Extrae los siguientes elementos específicos: {tipo_extraccion}")
    
    prompt_sistema = (
        "Eres un extractor de datos de alta precisión. Tu tarea es extraer la información solicitada del documento. "
        "Genera tu respuesta en formato JSON estructurado con la clave 'datos_extraidos'. "
        "Sé preciso y no agregues explicaciones fuera de la estructura de datos."
    )
    
    prompt_usuario = f"Instrucción: {instruccion}\n\nDocumento:\n{contenido[:25000]}"
    
    respuesta = await consultar_llm(prompt_sistema, prompt_usuario, ctx=ctx)
    try:
        if respuesta.strip().startswith("```json"):
            respuesta = respuesta.strip().split("```json")[1].split("```")[0].strip()
        return json.loads(respuesta)
    except Exception:
        return {"datos_extraidos": respuesta}


async def detectar_conflictos_impl(rutas_documentos: list[str], ctx: Any | None = None) -> list[dict[str, Any]]:
    """Detecta contradicciones entre múltiples documentos e identifica las fuentes."""
    textos = []
    for ruta in rutas_documentos:
        nombre = Path(ruta).name
        contenido = await leer_texto_documento(ruta)
        textos.append(f"Documento: {nombre}\nContenido:\n{contenido[:10000]}")
        
    contexto = "\n\n===\n\n".join(textos)
    
    prompt_sistema = (
        "Eres un auditor especializado en detección de discrepancias y conflictos contractuales o documentales. "
        "Analiza los siguientes textos y reporta cualquier contradicción en fechas, montos, nombres, tareas o acuerdos. "
        "Tu salida debe ser un JSON válido que sea una lista de objetos. Cada objeto debe tener: "
        "'conflicto' (descripción clara), 'fuentes' (nombres de los archivos en conflicto y lo que afirma cada uno), "
        "y 'resolucion_sugerida' (cómo se podría conciliar u optar según criterios de buenas prácticas)."
    )
    
    respuesta = await consultar_llm(prompt_sistema, contexto, ctx=ctx)
    try:
        if respuesta.strip().startswith("```json"):
            respuesta = respuesta.strip().split("```json")[1].split("```")[0].strip()
        return json.loads(respuesta)
    except Exception:
        return [{"conflicto": "Error de parseo", "respuesta_cruda": respuesta}]


async def generar_resumen_impl(ruta_documento: str, tipo_resumen: str = "executive", ctx: Any | None = None) -> str:
    """Genera un resumen en español: ejecutivo, detallado o en viñetas."""
    contenido = await leer_texto_documento(ruta_documento)
    
    guias = {
        "executive": "un resumen ejecutivo formal y conciso para alta gerencia (máximo 300 palabras).",
        "detailed": "un resumen analítico y detallado de las secciones principales del documento.",
        "bullets": "una lista clara y numerada de los puntos y conclusiones clave del documento."
    }
    
    guia = guias.get(tipo_resumen, guias["executive"])
    
    prompt_sistema = "Eres un redactor experto. Tu tarea es resumir el documento siguiendo la guía solicitada. Responde en español."
    prompt_usuario = f"Por favor genera {guia}\n\nDocumento:\n{contenido[:25000]}"
    
    return await consultar_llm(prompt_sistema, prompt_usuario, ctx=ctx)


# ─────────────────────────────────────────────────────────────────────────────
# TIER 2: GENERACIÓN AUTOMÁTICA
# ─────────────────────────────────────────────────────────────────────────────

async def crear_checklist_impl(ruta_documento: str, ctx: Any | None = None) -> dict[str, Any]:
    """Crea una lista interactiva de tareas basada en obligaciones, compromisos o guías en el documento."""
    contenido = await leer_texto_documento(ruta_documento)
    
    prompt_sistema = (
        "Analiza el documento y extrae todas las tareas, hitos obligatorios, entregables o acciones requeridas. "
        "Responde en formato JSON estructurado con una lista de tareas bajo la clave 'tareas'. "
        "Cada tarea debe tener: 'descripcion', 'responsable_sugerido' (si se menciona o infiere), y 'criterio_exito' (cómo saber si está completa)."
    )
    
    respuesta = await consultar_llm(prompt_sistema, f"Documento:\n{contenido[:20000]}", ctx=ctx)
    try:
        if respuesta.strip().startswith("```json"):
            respuesta = respuesta.strip().split("```json")[1].split("```")[0].strip()
        return json.loads(respuesta)
    except Exception:
        return {"tareas": [], "respuesta_cruda": respuesta}


async def extraer_cronograma_impl(ruta_documento: str, ctx: Any | None = None) -> list[dict[str, Any]]:
    """Extrae hitos y fechas en orden cronológico."""
    contenido = await leer_texto_documento(ruta_documento)
    
    prompt_sistema = (
        "Extrae todos los eventos con fecha de este documento. Genera un JSON que contenga una lista "
        "ordenada cronológicamente. Cada elemento debe ser un objeto con: 'fecha' (en formato YYYY-MM-DD o aproximado), "
        "'evento' (descripción de lo que ocurre), y 'prioridad' ('alta', 'media', 'baja')."
    )
    
    respuesta = await consultar_llm(prompt_sistema, f"Documento:\n{contenido[:20000]}", ctx=ctx)
    try:
        if respuesta.strip().startswith("```json"):
            respuesta = respuesta.strip().split("```json")[1].split("```")[0].strip()
        return json.loads(respuesta)
    except Exception:
        return [{"evento": "Error de procesamiento", "respuesta_cruda": respuesta}]


async def generar_rubrica_impl(ruta_documento: str, ctx: Any | None = None) -> dict[str, Any]:
    """Crea una rúbrica de evaluación con criterios, niveles de desempeño y puntajes basados en una guía o examen."""
    contenido = await leer_texto_documento(ruta_documento)
    
    prompt_sistema = (
        "Genera una rúbrica detallada en formato JSON a partir del documento guía de evaluación provisto. "
        "El JSON debe tener la clave 'criterios'. Cada criterio debe tener: 'nombre', 'descripcion', "
        "y un mapa de 'niveles' ('Excelente', 'Aceptable', 'Insuficiente') con su respectivo puntaje y descripción de expectativas."
    )
    
    respuesta = await consultar_llm(prompt_sistema, f"Documento:\n{contenido[:20000]}", ctx=ctx)
    try:
        if respuesta.strip().startswith("```json"):
            respuesta = respuesta.strip().split("```json")[1].split("```")[0].strip()
        return json.loads(respuesta)
    except Exception:
        return {"criterios": [], "respuesta_cruda": respuesta}


async def fusion_inteligente_impl(rutas_documentos: list[str], ctx: Any | None = None) -> str:
    """Combina información de varios documentos en un solo resumen unificado libre de duplicados."""
    textos = []
    for i, ruta in enumerate(rutas_documentos):
        contenido = await leer_texto_documento(ruta)
        textos.append(f"Documento {i+1} ({Path(ruta).name}):\n{contenido[:8000]}")
        
    contexto = "\n\n---\n\n".join(textos)
    
    prompt_sistema = (
        "Combina el contenido de estos documentos en un único documento maestro estructurado y coherente. "
        "Elimina redundancias, concilia diferencias de redacción y organiza la información por temas o secciones lógicas. "
        "Usa formato Markdown formal en español."
    )
    
    return await consultar_llm(prompt_sistema, contexto, max_tokens=4000, ctx=ctx)


# ─────────────────────────────────────────────────────────────────────────────
# TIER 3: VALIDACIÓN Y CALIDAD
# ─────────────────────────────────────────────────────────────────────────────

async def validar_estructura_impl(ruta_documento: str, ctx: Any | None = None) -> dict[str, Any]:
    """Evalúa si un documento sigue la estructura correcta formal y de estilo."""
    contenido = await leer_texto_documento(ruta_documento)
    
    prompt_sistema = (
        "Evalúa la estructura y el formato de este documento. Revisa consistencia en títulos, alineación conceptual, "
        "flujo e integridad. Responde en JSON con: 'es_valido' (bool), 'errores' (lista de fallos estructurales graves), "
        "'advertencias' (mejoras de formato sugeridas) y 'calificacion_general' (de 0 a 100)."
    )
    
    respuesta = await consultar_llm(prompt_sistema, f"Documento:\n{contenido[:20000]}", ctx=ctx)
    try:
        if respuesta.strip().startswith("```json"):
            respuesta = respuesta.strip().split("```json")[1].split("```")[0].strip()
        return json.loads(respuesta)
    except Exception:
        return {"error": "Error al analizar", "respuesta_cruda": respuesta}


async def calidad_ocr_impl(ruta_documento: str, ctx: Any | None = None) -> dict[str, Any]:
    """Analiza si el texto extraído del documento contiene ruido de OCR (caracteres basura, mala segmentación)."""
    contenido = await leer_texto_documento(ruta_documento)
    
    # Tomar muestras del inicio, medio y fin
    largo = len(contenido)
    muestras = []
    if largo > 0:
        muestras.append(contenido[:1500])
    if largo > 6000:
        muestras.append(contenido[largo//2 : largo//2 + 1500])
    if largo > 12000:
        muestras.append(contenido[-1500:])
        
    contexto_muestra = "\n\n[MUESTRA]\n".join(muestras)
    
    prompt_sistema = (
        "Analiza las siguientes muestras de texto extraídas de un documento para evaluar la calidad del OCR. "
        "Busca caracteres extraños (como $, #, @ mal puestos), palabras cortadas, saltos de línea incorrectos o ruido. "
        "Responde en JSON con: 'puntuacion_calidad' (0 a 100, donde 100 es perfecto), 'ruido_detectado' (true/false), "
        "'ejemplos_ruido' (lista de ejemplos) y 'sugerencia_reprocesar' (true/false)."
    )
    
    respuesta = await consultar_llm(prompt_sistema, contexto_muestra, ctx=ctx)
    try:
        if respuesta.strip().startswith("```json"):
            respuesta = respuesta.strip().split("```json")[1].split("```")[0].strip()
        return json.loads(respuesta)
    except Exception:
        return {"puntuacion_calidad": 50, "error": "No se pudo parsear", "respuesta_cruda": respuesta}


async def mapa_referencias_impl(rutas_documentos: list[str], ctx: Any | None = None) -> dict[str, Any]:
    """Mapea referencias y menciones cruzadas entre documentos."""
    referencias = {}
    for ruta in rutas_documentos:
        nombre = Path(ruta).name
        contenido = await leer_texto_documento(ruta)
        referencias[nombre] = contenido[:6000] # muestra para referencias
        
    contexto = json.dumps(referencias, ensure_ascii=False)
    
    prompt_sistema = (
        "Analiza los siguientes documentos y crea un mapa de referencias cruzadas. Identifica qué documento menciona "
        "conceptos, leyes, normativas, fechas o acuerdos de los otros. Responde en JSON con una lista de relaciones: "
        "'origen' (nombre del documento), 'destino' (nombre del documento citado o referenciado), "
        "'contexto_referencia' (por qué se relacionan)."
    )
    
    respuesta = await consultar_llm(prompt_sistema, contexto, ctx=ctx)
    try:
        if respuesta.strip().startswith("```json"):
            respuesta = respuesta.strip().split("```json")[1].split("```")[0].strip()
        return json.loads(respuesta)
    except Exception:
        return {"relaciones": [], "respuesta_cruda": respuesta}


async def verificacion_completitud_impl(ruta_documento: str, secciones_esperadas: list[str], ctx: Any | None = None) -> dict[str, Any]:
    """Verifica si el documento tiene las secciones exigidas por una plantilla o directiva."""
    contenido = await leer_texto_documento(ruta_documento)
    
    contexto_solicitud = {
        "secciones_esperadas": secciones_esperadas,
        "documento_inicio": contenido[:20000]
    }
    
    prompt_sistema = (
        "Eres un validador de completitud. Revisa si en el documento se desarrollan o mencionan claramente las secciones "
        "solicitadas. Genera un reporte JSON con: 'completo' (bool), 'secciones_encontradas' (lista de secciones que sí están), "
        "'secciones_faltantes' (lista de secciones no encontradas) y 'comentarios' (breve descripción para mejorar el documento)."
    )
    
    respuesta = await consultar_llm(prompt_sistema, json.dumps(contexto_solicitud, ensure_ascii=False), ctx=ctx)
    try:
        if respuesta.strip().startswith("```json"):
            respuesta = respuesta.strip().split("```json")[1].split("```")[0].strip()
        return json.loads(respuesta)
    except Exception:
        return {"completo": False, "error": "Fallo al procesar", "respuesta_cruda": respuesta}


# ─────────────────────────────────────────────────────────────────────────────
# TIER 4: AUTOMATIZACIÓN AVANZADA
# ─────────────────────────────────────────────────────────────────────────────

async def procesar_lote_impl(ruta_carpeta: str, operacion: str, filtro_extension: str = "*", ctx: Any | None = None) -> dict[str, Any]:
    """Procesa recursivamente todos los documentos en una carpeta aplicando una acción común."""
    carpeta = Path(ruta_carpeta)
    if not carpeta.is_dir():
        return {"success": False, "error": f"La ruta {ruta_carpeta} no es un directorio válido."}
        
    archivos = []
    # Buscar archivos
    extensiones_validas = (".pdf", ".docx", ".txt", ".md")
    for elem in carpeta.iterdir():
        if elem.is_file() and elem.suffix.lower() in extensiones_validas:
            if filtro_extension == "*" or elem.suffix.lower() == filtro_extension.lower():
                archivos.append(elem)
                
    if not archivos:
        return {"success": True, "mensaje": "No se encontraron archivos válidos en la carpeta.", "resultados": {}}
        
    resultados = {}
    for archivo in archivos[:10]: # Limitar a 10 archivos para evitar cuellos de botella
        try:
            if operacion == "resumen":
                res = await generar_resumen_impl(str(archivo), "executive", ctx=ctx)
                resultados[archivo.name] = {"resumen": res}
            elif operacion == "cronograma":
                res_cron = await extraer_cronograma_impl(str(archivo), ctx=ctx)
                resultados[archivo.name] = {"cronograma": res_cron}
            elif operacion == "calidad":
                res_cal = await calidad_ocr_impl(str(archivo), ctx=ctx)
                resultados[archivo.name] = {"calidad": res_cal}
            else:
                resultados[archivo.name] = {"error": f"Operación '{operacion}' no soportada en procesamiento por lotes."}
        except Exception as e:
            resultados[archivo.name] = {"error": str(e)}
            
    return {
        "success": True,
        "operacion": operacion,
        "total_archivos": len(archivos),
        "procesados": len(resultados),
        "resultados": resultados
    }


async def seguimiento_versiones_impl(ruta_doc1: str, ruta_doc2: str, ctx: Any | None = None) -> dict[str, Any]:
    """Compara detalladamente dos versiones de un documento para extraer diferencias conceptuales."""
    doc1 = await leer_texto_documento(ruta_doc1)
    doc2 = await leer_texto_documento(ruta_doc2)
    
    prompt_sistema = (
        "Analiza estas dos versiones del mismo documento e identifica cambios sustanciales (adiciones, eliminaciones "
        "y reformulaciones críticas). Ignora cambios menores de formato o tipografía. Responde en JSON con la clave "
        "'cambios'. Cada elemento de la lista debe tener: 'tipo' ('adicion', 'eliminacion', 'modificacion'), "
        "'descripcion_cambio' e 'impacto_estimado'."
    )
    
    prompt_usuario = f"Versión 1:\n{doc1[:12000]}\n\nVersión 2:\n{doc2[:12000]}"
    
    respuesta = await consultar_llm(prompt_sistema, prompt_usuario, ctx=ctx)
    try:
        if respuesta.strip().startswith("```json"):
            respuesta = respuesta.strip().split("```json")[1].split("```")[0].strip()
        return json.loads(respuesta)
    except Exception:
        return {"cambios": [], "respuesta_cruda": respuesta}


async def crear_indice_impl(ruta_documento: str, ctx: Any | None = None) -> dict[str, Any]:
    """Crea una lista detallada de temas clave con su explicación."""
    contenido = await leer_texto_documento(ruta_documento)
    
    prompt_sistema = (
        "Crea un índice temático del documento. Identifica los conceptos más relevantes explicados. "
        "Genera un JSON con la clave 'indice_temas'. Cada tema debe poseer: 'concepto', 'contexto_resumen' "
        "y 'palabras_clave_relacionadas'."
    )
    
    respuesta = await consultar_llm(prompt_sistema, f"Documento:\n{contenido[:20000]}", ctx=ctx)
    try:
        if respuesta.strip().startswith("```json"):
            respuesta = respuesta.strip().split("```json")[1].split("```")[0].strip()
        return json.loads(respuesta)
    except Exception:
        return {"indice_temas": [], "respuesta_cruda": respuesta}


async def extraer_relaciones_impl(rutas_documentos: list[str], ctx: Any | None = None) -> dict[str, Any]:
    """Genera un grafo JSON estructurado de personas, organizaciones, fechas y sus lazos."""
    textos = []
    for ruta in rutas_documentos:
        nombre = Path(ruta).name
        contenido = await leer_texto_documento(ruta)
        textos.append(f"Doc: {nombre}\n{contenido[:8000]}")
        
    contexto = "\n\n---\n\n".join(textos)
    
    prompt_sistema = (
        "Genera un grafo de relaciones en JSON. Identifica Entidades (Personas, Organizaciones, Proyectos, Fechas) "
        "y los Enlaces o Relaciones que las unen basadas en la lectura de los textos. El JSON debe tener la estructura: "
        "'nodos': [{'id': 'nombre_entidad', 'tipo': 'Persona|Organizacion|Fecha|Concepto'}], "
        "y 'enlaces': [{'origen': 'id_nodo', 'destino': 'id_nodo', 'relacion': 'descripcion_de_la_conexion'}]."
    )
    
    respuesta = await consultar_llm(prompt_sistema, contexto, ctx=ctx)
    try:
        if respuesta.strip().startswith("```json"):
            respuesta = respuesta.strip().split("```json")[1].split("```")[0].strip()
        return json.loads(respuesta)
    except Exception:
        return {"nodos": [], "enlaces": [], "respuesta_cruda": respuesta}


# ─────────────────────────────────────────────────────────────────────────────
# TIER 5: GENERACIÓN INTELIGENTE
# ─────────────────────────────────────────────────────────────────────────────

async def generar_preguntas_respuestas_impl(ruta_documento: str, ctx: Any | None = None) -> list[dict[str, Any]]:
    """Genera preguntas y respuestas conceptuales de autoevaluación."""
    contenido = await leer_texto_documento(ruta_documento)
    
    prompt_sistema = (
        "Genera un set de 10 preguntas y respuestas de autoevaluación para verificar la comprensión de este documento. "
        "Responde estrictamente en un JSON que sea una lista de objetos. Cada objeto debe poseer: "
        "'pregunta' y 'respuesta_esperada' redactada de forma profesional."
    )
    
    respuesta = await consultar_llm(prompt_sistema, f"Documento:\n{contenido[:20000]}", ctx=ctx)
    try:
        if respuesta.strip().startswith("```json"):
            respuesta = respuesta.strip().split("```json")[1].split("```")[0].strip()
        return json.loads(respuesta)
    except Exception:
        return [{"pregunta": "Error al generar", "respuesta_esperada": respuesta}]


async def briefing_ejecutivo_impl(rutas_documentos: list[str], ctx: Any | None = None) -> str:
    """Genera un reporte consolidado ultra-condensado de 1 página."""
    textos = []
    for ruta in rutas_documentos:
        nombre = Path(ruta).name
        contenido = await leer_texto_documento(ruta)
        textos.append(f"Expediente: {nombre}\n{contenido[:8000]}")
        
    contexto = "\n\n---\n\n".join(textos)
    
    prompt_sistema = (
        "Eres un asesor municipal experto. Tu cliente necesita un Briefing Ejecutivo de 1 página que resuma y conecte "
        "el contenido de los siguientes documentos. Sé directo, estructurado y enfocado en la toma de decisiones. "
        "Usa formato Markdown formal en español con títulos y viñetas estructuradas."
    )
    
    return await consultar_groq(prompt_sistema, contexto, max_tokens=3000)


async def generar_items_accion_impl(ruta_documento: str) -> list[dict[str, Any]]:
    """Extrae planes de acción y tareas específicas."""
    contenido = await leer_texto_documento(ruta_documento)
    
    prompt_sistema = (
        "Extrae una lista de tareas de acción (action items) del documento. Cada item debe tener: "
        "'tarea' (qué se debe hacer), 'responsable' (quién), 'plazo' (cuándo) e 'impacto' ('alto', 'medio', 'baba'). "
        "Entrega tu resultado como una lista JSON válida."
    )
    
    respuesta = await consultar_groq(prompt_sistema, f"Documento:\n{contenido[:20000]}")
    try:
        if respuesta.strip().startswith("```json"):
            respuesta = respuesta.strip().split("```json")[1].split("```")[0].strip()
        return json.loads(respuesta)
    except Exception:
        return [{"tarea": "Fallo al procesar", "responsable": "N/A", "plazo": "N/A", "respuesta_cruda": respuesta}]
