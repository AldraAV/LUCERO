# 🛑 MANUAL DE EMERGENCIA Y RESOLUCIÓN DE ERRORES DE LUCERO

> **ESTATUS: MANDATORIO Y VINCULANTE**
> Este documento rige el protocolo obligatorio para diagnosticar, reparar o refactorizar el servidor MCP de LUCERO.

## 1. Regla de Oro en caso de Fallas

Si el servidor MCP de LUCERO presenta cualquiera de los siguientes problemas:
- Arroja excepciones al interactuar con archivos OOXML.
- Se congela o deja de responder (*Silent Crash* del watcher de FastMCP).
- Requiere modificaciones estructurales profundas en `server.py` o `surgeon.py`.

**QUEDA ESTRICTAMENTE PROHIBIDO intentar arreglarlo improvisando o usando scripts de un solo uso.**

## 2. Cadena de Skills y Agentes Obligatorios

Cualquier agente de IA que sea instruido para reparar LUCERO **DEBE** invocar o cargar obligatoriamente el siguiente conjunto de herramientas y metodologías antes de tocar una sola línea de código:

### 🧩 Fundamentos del Servidor MCP
- `/mcp-builder`
- `/python_mcp_server`
- `/mcp_best_practices`
- `/tool-mcp`
- `/protect-mcp-setup`

### 🛡️ Trazabilidad y Prevención de Pérdida
- `/signed-audit-trails-recipe`
- `/accidental-data-loss-prevention` (Extrema precaución con la corrupción del `document.xml`)

### 🔍 Depuración Quirúrgica
- `/find-bugs`
- `/diagnosing-bugs`
- `/error-debugging-error-analysis`
- `/error-debugging-error-trace`

### 🤖 Orquestación Multi-Agente (Obligatoria vía `/teamwork-preview`)
Para la ejecución, DEBE usarse el entorno `/teamwork-preview` invocando en conjunto a los siguientes subagentes especialistas:
- **Backend Architect** (Estructura y flujos del MCP)
- **API Platform Engineer** (Integración y robustez del protocolo)
- **API Tester** (Pruebas rigurosas sobre las respuestas JSON-RPC/OOXML)
- **Application Security Engineer** (Validación de inyecciones y permisos)
- **AI Engineer** (Manejo de asfixia de contexto y formateo LLM-friendly, ej. TOON)

- `/multi-agent-patterns` (División de tareas: Validación, Edición, Testing)

### 🍒 Soberanía del Aldraverso y Calidad
- `/mano-derecha-aldraverso` (Evaluación de AST antes de escribir, prevención de excepciones).
- `/arquitecto-aldraverso` (Español soberano, patrones de diseño).
- `/lucero` (Reglas nativas de este mismo servidor).

### 📖 Consolidación Institucional
- `/learn` (Cada victoria o corrección mayor debe documentarse permanentemente).

## 3. Procedimiento

1. Lee y asimila los protocolos de las skills mencionadas.
2. Analiza el problema reportado.
3. Propón una solución usando el enfoque *Mano Derecha* (PSP Aligerado).
4. Aplica los cambios protegiendo la estructura JSON/XML y verificando las sintaxis de importaciones y variables.
5. Pide al usuario que reinicie la sesión o aplicación para limpiar la caché de FastMCP si es necesario.
