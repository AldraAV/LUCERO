---
name: lucero
description: Guía maestra para LUCERO — servidor MCP de manipulación quirúrgica OOXML y generación profesional de documentos .docx. Úsala siempre que necesites interactuar, inspeccionar, editar, generar o extraer metadatos de documentos.
---

# 🍌 LUCERO MCP

**Ubicación del proyecto:** [`C:\Users\carde\Desktop\MUACK_2.0\LUCERO`](file:///C:/Users/carde/Desktop/MUACK_2.0/LUCERO)  
**Entorno virtual:** `LUCERO\.venv` (Python 3.11+)  
**Autor:** AldraAV (manhalev1520@gmail.com)  
**Entrypoint MCP:** `src.server:run` (alias: `aldradoc`)  
**Skill embebida en el repo:** [`LUCERO/.agent/skills/lucero/SKILL.md`](file:///C:/Users/carde/Desktop/MUACK_2.0/LUCERO/.agent/skills/lucero/SKILL.md) y [`LUCERO/skills/lucero/SKILL.md`](file:///C:/Users/carde/Desktop/MUACK_2.0/LUCERO/skills/lucero/SKILL.md)

## Documentación Normativa y Enlaces Cruzados
- **Normas de Formato APA 7ma:** [`APA_7_RULES.md`](file:///C:/Users/carde/Desktop/MUACK_2.0/LUCERO/APA_7_RULES.md)
- **Guía de Redacción Académica y Antipatrones de IA:** [`GUIA_REDACCION_ACADEMICA_Y_ANTIPATRONES_IA.md`](file:///C:/Users/carde/Desktop/MUACK_2.0/LUCERO/GUIA_REDACCION_ACADEMICA_Y_ANTIPATRONES_IA.md)
- **Resolución de Errores y Diagnóstico:** [`RESOLUCION_ERRORES.md`](file:///C:/Users/carde/Desktop/MUACK_2.0/LUCERO/RESOLUCION_ERRORES.md)
- **Referencia Interna de Antipatrones:** [`references/redaccion_academica_y_antipatrones_ia.md`](file:///C:/Users/carde/Desktop/MUACK_2.0/.agent/skills/lucero/references/redaccion_academica_y_antipatrones_ia.md)

## Qué es LUCERO

Servidor MCP de alto nivel con **más de 25 herramientas activas** agrupadas en 5 TIERS (capas). TODAS las herramientas descritas a continuación están implementadas, programadas y expuestas a través del protocolo MCP para ser invocadas nativamente. Permiten desde la manipulación quirúrgica XML de archivos `.docx` hasta el análisis cruzado de documentos mediante Inteligencia Artificial.

## 🚨 Reglas de Oro (Quirúrgicas)

### 1. stdout está PROHIBIDO
El protocolo MCP usa `stdout` exclusivamente para JSON-RPC. Nunca agregues `print()` al código fuente de LUCERO. Siempre usa el logger interno provisto.

### 2. El Fenómeno del "Logo Aplastado"
Cuando usas `surgical_replace_image`, solo se reemplazan los **píxeles**. Para ajustar dimensiones deformadas, invoca inmediatamente después `surgical_style_edit` sobre el XPath de la imagen para redefinir `cx` y `cy`.

### 3. Headers vs Document
`inspect_images` solo escanea `document.xml`. Para imágenes institucionales que están en `word/header1.xml`, usa `zip_target` directo en `surgical_replace_image` (ej. `zip_target="word/media/image3.jpeg"`).

### 4. XPath: Usa Absolutos o por Texto
- ❌ `//w:p[2]` — puede fallar.
- ✅ `(//w:body//w:p)[2]` o `//w:t[contains(text(), "Conclusiones")]`

### 5. Vínculo Simbólico Normativo (APA 7ma Edición)
**OBLIGATORIO:** Todo formato OOXML, inyección de tablas, viñetas, listas, jerarquías de títulos, figuras y tipografía orquestado a través de LUCERO **DEBE** someterse a las reglas establecidas en el archivo normativo raíz:
👉 [`APA_7_RULES.md`](file:///C:/Users/carde/Desktop/MUACK_2.0/LUCERO/APA_7_RULES.md)
Queda estrictamente prohibido improvisar estilos, aplicar parches paliativos que rompan los niveles de Títulos (Headings 1-5), o inventar formatos de viñetas. Si LUCERO detecta un formato ajeno a la norma, deberá normalizarlo.

### 6. Protocolo de Calidad Académica y Prevención de Antipatrones de IA (Erradicación de Viñetas)
**OBLIGATORIO:** En documentos académicos, protocolos de investigación y tesis técnicas, LUCERO debe aplicar de forma inexcusable el protocolo contenido en:
👉 [`GUIA_REDACCION_ACADEMICA_Y_ANTIPATRONES_IA.md`](file:///C:/Users/carde/Desktop/MUACK_2.0/LUCERO/GUIA_REDACCION_ACADEMICA_Y_ANTIPATRONES_IA.md) y [`references/redaccion_academica_y_antipatrones_ia.md`](file:///C:/Users/carde/Desktop/MUACK_2.0/.agent/skills/lucero/references/redaccion_academica_y_antipatrones_ia.md)
- **Prohibición de "Bullet-Pointitis":** Prohibido abusar de viñetas (`w:numPr`) o listas telegráficas en justificaciones, análisis de encuestas o características. Toda argumentación debe estructurarse en **prosa analítica continua** con conectores lógicos intrapárrafo e interpárrafo.
- **Cero AI-Puffery:** Erradicar adjetivos hiperbólicos vacíos ("crucial", "vital", "revolucionario", "piedra angular"). Cada afirmación técnica debe sostenerse en métricas empíricas verificables.
- **Desglose de Fórmulas:** Toda ecuación (muestreo, finanzas) debe desplegar sus variables y sustitución numérica paso a paso.
- **Tablas Abiertas APA 7:** Exclusivamente 3 líneas horizontales maestras; cero mallas cerradas de celda.

---

## 🔧 Las 5 Capas (TIERS) de Herramientas MCP Activas

### TIER 1 — Lectura e Inspección (Inspección y Extracción)
Úsalas para abrir contenedores y leer datos antes de operar:
*   `inspect_xml_tree`: Genera el mapa estructural (XPaths, IDs, estilos) del documento. Invocala SIEMPRE antes de operar quirúrgicamente.
*   `inspect_images`: Extrae el listado de relaciones (`rId`) y rutas internas de imágenes.
*   `pro_read_document`: Extrae el contenido en texto plano o markdown desde DOCX, PDF, MD o TXT.
*   `compare_documents`: Analiza múltiples archivos buscando vacíos de información o redundancias semánticas.
*   `extract_selective`: Extrae selectivamente fechas, tablas o nombres de un archivo sin extraer el texto completo.
*   `inspect_excel_sheets`: Inspecciona metadatos, dimensiones ('A1:F40'), visibilidad y tablas de todas las hojas de un libro Excel (.xlsx/.xlsm).
*   `inspect_excel_cells`: Inspecciona celdas, valores, fórmulas, tipos de datos y estilos detallados en un rango de cálculo.

### TIER 2 — Cirugía OOXML (Bisturí XML)
Úsalas para la mutación ultra-precisa sobre el árbol XML (`document.xml`) sin corromper el estilo circundante:
*   `surgical_replace`: Reemplaza texto en nodos `<w:t>` garantizando la preservación al 100% de propiedades como negritas y color.
*   `surgical_replace_image`: Sustituye un binario de imagen en el ZIP de un DOCX.
*   `surgical_style_edit`: Modifica propiedades de formato directo (fuentes, sangrías, márgenes) en `<w:pPr>` / `<w:rPr>`.
*   `surgical_inject_image`: Inserta un elemento `<w:drawing>` nuevo en un XPath.
*   `inject_toc`: Inyecta un bloque de Tabla de Contenidos nativa de Word con hipervínculos internos.
*   `run_xpath`: Corre expresiones XPath libres sobre el XML para depuración extrema.
*   `commit_changes`: Consolida y reempaqueta un DOCX modificado externamente o en lote.
*   `surgical_replace_excel_cell`: Modifica atómicamente una celda en Excel (valor o fórmula) preservando el 100% de estilos y formatos originales (zero format loss).
*   `surgical_inject_excel_table`: Inyecta tablas de datos con autoajuste métrico de columnas y opción de paleta sobria Aurora.
*   `surgical_search_replace_excel`: Búsqueda y reemplazo quirúrgico de cadenas en libros Excel sin corromper fórmulas ni formatos.

### TIER 3 — Generación Profesional (Nativos y Estilos)
Úsalas para inyectar o construir documentos respetando plantillas y normas académicas:
*   `inject_apa_structure`: Inyecta de manera nativa bloques APA 7ª (headings, párrafos, notas de figura) sin romper el layout.
*   `list_apa_templates`: Devuelve el catálogo completo de plantillas APA disponibles para inyección.
*   `pro_write_document`: Escribe o modifica un archivo a partir de sintaxis Markdown y lo exporta a DOCX, MD o TXT.

### TIER 4 — Conversión & Export (Headless y Lotes)
Úsalas para flujos de archivos masivos o transformación de formatos finales:
*   `pro_transform_document`: Convierte de DOCX a PDF (usando motores headless) o de DOCX a MD.
*   `pro_encrypt_document`: Cifra archivos finales usando encriptación AES-256.

### TIER 5 — IA Documental (Procesamiento Semántico Élite)
Úsalas para realizar razonamiento complejo y análisis avanzado de expedientes usando IA de lenguaje:
*   `generate_summary`: Crea resúmenes ejecutivos, analíticos o viñetas sobre documentos densos.
*   `create_checklist`: Lee pliegos, manuales o lineamientos y devuelve un checklist JSON con los requisitos.
*   `extract_timeline`: Genera cronogramas cronológicos basados en todos los hitos y fechas halladas en un texto.
*   `generate_qa_pairs`: Genera un cuestionario estructurado (preguntas y respuestas) a partir de la fuente académica o laboral.
*   `create_executive_brief`: Procesa una lista de múltiples expedientes (PDF/DOCX) y condensa todo en un reporte ejecutivo de una página.
*   `generate_action_items`: Extrae tareas accionables, infiriendo responsables y plazos (ideal para minutas de reuniones).
*   `detect_conflicts`: Realiza evaluación cruzada entre varios documentos para detectar discrepancias y contradicciones de datos o políticas.
*   `version_tracking`: Compara una versión anterior con una actual, listando qué conceptos o reglas fueron modificados.
*   `create_index`: Construye un mapa temático profundo de los temas tratados.
*   `extract_relationships`: Devuelve el grafo (personas, entidades, leyes) extraídas de documentos densos.
*   `generate_rubric`: A partir de un texto académico, elabora una rúbrica estructurada de ponderaciones y criterios.
*   `smart_merge`: Elimina duplicidades en distintos reportes y redacta uno solo unificado y magistral.
*   `validate_structure`: Evalúa qué tan formal y estéticamente robusto es el diseño del documento analizado.
*   `ocr_quality_score`: Identifica corrupciones de texto o ruido (si provienen de escaneos defectuosos).
*   `cross_reference`: Rastrea y mapea las relaciones de cita implícitas entre distintos archivos.
*   `completeness_check`: Audita un archivo verificando que no falte ninguna de las secciones obligatorias pasadas como argumento.

---

## 📊 Árbol de Decisión Práctico (CÓMO operar)

1. **Si quieres generar un documento Word base o Markdown**:
   Usa `pro_write_document` y mándale sintaxis Markdown normal si es sencillo. Si es académico riguroso, inyecta con `inject_apa_structure`.
2. **Si necesitas extraer inteligencia o datos de un PDF**:
   Usa las herramientas de TIER 5: `extract_timeline` si buscas fechas, `generate_action_items` si buscas minutas, `create_checklist` si es un manual de reglas.
3. **Si el usuario quiere saber si dos leyes o textos se contradicen**:
   Pasa ambos a `detect_conflicts` (TIER 5) para cruce semántico automático.
4. **Si debes editar texto en un Word, preservando colores y tipografías (sin romper el XML)**:
   Abre con `inspect_xml_tree`, identifica la cadena de texto exacta en un `w:t`, y usa `surgical_replace`.


### 🛑 REGLA DE CERO ASUNCIONES (PRE-FLIGHT AUDIT MANDATORY)
Antes de ejecutar CUALQUIER comando de escritura (`surgical_replace`, `inject_apa_structure`, `lote_quirurgico`), es **OBLIGATORIO** auditar la estructura XML del documento para prevenir corrupción de formato y pérdida accidental de datos.

1. **Jamás asumas el formato:** Si el usuario pide modificar una "tabla", no busques la palabra "Tabla" en texto plano. Usa `run_xpath` con `//w:tbl` o audita el XML nativo para confirmar su existencia.
2. **Revisión de Estilos:** Antes de inyectar bloques APA cerca de encabezados, verifica el `w:pStyle` de los párrafos adyacentes para evitar herencias de estilos de Título (`Ttulo1`, `Ttulo2`) que contaminen el Índice de Contenido (TOC).
3. **Validación de Viñetas e Imágenes:** Mapea el documento buscando `<w:drawing>` y `<w:numPr>` explícitamente para obtener un contexto estructural real.


### 🛑 REGLA ANTI-SCRIPTS PALIATIVOS (STRICT ENFORCEMENT)
Si la manipulación estructural de un DOCX requiere operaciones masivas, algorítmicas o condicionales que exceden la capacidad de las herramientas MCP expuestas (por ejemplo: cambiar decenas de estilos simultáneamente, limpiar viñetas masivamente o normalizar formatos de figuras), **QUEDA ESTRICTAMENTE PROHIBIDO** crear scripts de Python independientes (`scratch/*.py`) que importen las librerías internas de LUCERO para saltarse las limitaciones del servidor. 

**Flujo obligatorio:**
1. DEBES actualizar el código fuente del servidor MCP de LUCERO (editando `src/surgeon.py` y `src/server.py`).
2. Agrega la nueva herramienta nativa (ej. `bulk_style_replace`, `normalize_apa_figures`, etc.).
3. Pídele al usuario que recargue la ventana (`Ctrl + Mayusc + R`) e invoca la herramienta directamente vía MCP. 
**LUCERO debe evolucionar; jamás debe ser parcheado con scripts de un solo uso.**

### 🛑 RESOLUCIÓN DE ERRORES DE LUCERO (MANDATORIO)
Cuando el servidor MCP de LUCERO falle, arroje excepciones, se congele (*Silent Crash* de FastMCP), o requiera refactorización estructural, **ES OBLIGATORIO** emplear la siguiente combinación de agentes y habilidades. Queda estrictamente prohibido intentar arreglar el servidor sin aplicar este marco de trabajo:

- **Habilidades Core del Servidor:** `/mcp-builder`, `/python_mcp_server`, `/mcp_best_practices`, `/tool-mcp`, `/protect-mcp-setup`
- **Trazabilidad y Prevención:** `/signed-audit-trails-recipe`, `/accidental-data-loss-prevention`
- **Depuración Quirúrgica:** `/find-bugs`, `/diagnosing-bugs`, `/error-debugging-error-analysis`, `/error-debugging-error-trace`
- **Orquestación Multi-Agente (Obligatoria vía `/teamwork-preview`):**
  - **Backend Architect** (Estructura y flujos del MCP)
  - **API Platform Engineer** (Integración y robustez del protocolo)
  - **API Tester** (Pruebas rigurosas sobre las respuestas JSON-RPC/OOXML)
  - **Application Security Engineer** (Validación de inyecciones y permisos)
  - **AI Engineer** (Manejo de asfixia de contexto y formateo LLM-friendly, ej. TOON)
  - `/multi-agent-patterns` (División de tareas: Validación, Edición, Testing)
- **Soberanía y Diseño de Código:** `/mano-derecha-aldraverso` (PSP Aligerado, Validación AST pre-ejecución), `/arquitecto-aldraverso`
- **El propio Servidor:** `/lucero`
- **Memoria Institucional:** `/learn` (para consolidar fixes permanentes y evitar recaídas)

Cualquier agente encargado de tocar `server.py`, `surgeon.py` o dependencias de LUCERO debe procesar esta cadena de directivas para asegurar que el servidor sea reparado sin causar asfixia de contexto ni corromper las herramientas existentes.
