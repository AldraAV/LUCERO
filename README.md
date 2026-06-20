# LUCERO — El Décimo Hermano

> **"Mientras otros editores suponen dónde está el texto, SURGEON lo encuentra por coordenadas exactas en el árbol XML."**

---

## ¿Por qué este servidor es superior?

| Capacidad | Editores estándar | **LUCERO** |
|-----------|-------------------|----------------------|
| Localización de texto | Busca string en texto plano | XPath exacto sobre nodos `<w:t>` |
| Cambiar una palabra | Regenera el párrafo completo | Toca **solo** el nodo objetivo |
| Formato tras edición | Puede perder negrita/color | **Zero format loss** garantizado |
| Texto fragmentado en runs | Falla silenciosamente | Fusión automática de multi-runs |
| Inyección APA 7ª | Texto plano sin estilos reales | XML OOXML nativo con estilos completos |
| Reempaquetado | Riesgo de corromper el ZIP | Preserva `[Content_Types].xml` byte a byte |

---

## Stack Tecnológico

- **Python 3.11+** con anotaciones de tipo completas
- **FastMCP** (`mcp[cli]`) — SDK oficial de Model Context Protocol
- **lxml** — Parser y evaluador XPath de alto rendimiento (libxml2)
- **python-docx** — Interfaz de alto nivel donde aplica
- **zipfile** stdlib — Manejo seguro del contenedor DOCX

---

## Estructura del Proyecto

```
LUCERO/
├── src/
│   ├── __init__.py
│   ├── server.py          # FastMCP server — 6 tools
│   ├── surgeon.py         # Motor quirúrgico: XPath + lxml
│   ├── apa_templates.py   # Plantillas OOXML para APA 7ª
│   └── utils.py           # Namespaces ECMA-376, logger, helpers
├── tests/
│   ├── __init__.py
│   └── test_surgeon.py    # Suite completa con DOCX real como fixture
├── docs/
│   └── ooxml_reference.md # Referencia rápida de namespaces y tags
├── pyproject.toml
└── README.md
```

---

## Instalación

```bash
# Clonar y entrar al directorio
cd LUCERO

# Instalar con pnpm (wrapper de pip para entornos Python)
pip install -e ".[dev]"

# O directamente con pip
pip install mcp[cli] lxml python-docx
```

---

## Herramientas MCP (Tools)

> 💡 **Arquitectura de 5 Capas (Tiers)**: Para ver el mapa completo de las 20+ herramientas organizadas por Tiers de funcionalidad, firmas de parámetros y casos de uso, consulta el documento principal [LUCERO_SUITE_TIERS.md](file:///C:/Users/carde/Desktop/MUACK/LUCERO_SUITE_TIERS.md) en la raíz del workspace.

### 1. `inspect_xml_tree`
Devuelve el mapa estructural completo del DOCX: cada párrafo con su `paraId`,
estilo, texto y los runs individuales con su formato real (bold, italic, etc.)
y su XPath exacto. Esto permite que el LLM "vea" la estructura oculta antes de operar.

```json
{
  "para_index": 5,
  "style": "ParrafoAPA",
  "text": "Se procedió a activar el entorno virtual...",
  "runs": [
    {
      "run_index": 0,
      "text": "Se procedió a ",
      "format": { "bold": false, "italic": false },
      "xpath": "//w:body//w:p[6]/w:r[1]"
    }
  ]
}
```

### 2. `surgical_replace`
Localiza texto mediante XPath y reemplaza **solo** el contenido de `<w:t>`,
dejando intactas todas las etiquetas de formato (`<w:rPr>`, negrita, color, tamaño).
Maneja automáticamente texto fragmentado en múltiples runs consecutivos.

### 3. `inject_apa_structure`
Inyecta bloques XML OOXML nativos (no texto plano) en la posición exacta
indicada por un texto de anclaje. Soporta:
- `heading1/2/3` — Encabezados APA 7ª con estilos correctos
- `body_paragraph` — Párrafo con sangría de primera línea y doble espacio
- `figure_label` — "Figura N" en negrita + título en cursiva
- `figure_note` — "Nota." en cursiva + texto de la nota
- `reference` — Entrada de referencia con sangría francesa

### 4. `commit_changes`
Reempaqueta el ZIP asegurando que `[Content_Types].xml`, relaciones,
imágenes y metadatos se mantengan íntegros. Solo sobreescribe `word/document.xml`.

### 5. `list_apa_templates`
Catálogo de todas las plantillas disponibles con descripción y parámetros extra.

### 6. `run_xpath`
Ejecuta expresiones XPath arbitrarias sobre el `document.xml`. Para exploración
avanzada y diagnóstico quirúrgico.

---

## Flujo de Trabajo Recomendado

```
1. inspect_xml_tree  → Conoce la estructura real antes de operar
2. surgical_replace  → Corrige texto sin tocar el formato
3. inject_apa_structure → Inserta bloques académicos donde necesites
4. commit_changes    → Un solo commit limpio al final
```

---

## Ejecución del Servidor

```bash
# Modo desarrollo (stdio, para Claude Desktop)
python -m src.server

# O via entrypoint
aldradoc
```

### Configuración en Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "lucero": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "C:\\Users\\carde\\Desktop\\MUACK\\LUCERO"
    }
  }
}
```

---

## Ejecutar los Tests

```bash
pytest tests/ -v
```

Los tests usan `Caso_practico_u3_FINAL.docx` como fixture de prueba real,
asegurando que el servidor opere correctamente sobre documentos del mundo real.

---

## Namespaces ECMA-376 Clave

| Prefijo | URI | Uso |
|---------|-----|-----|
| `w:` | `...wordprocessingml/2006/main` | Todo el contenido del documento |
| `w14:` | `...office/word/2010/wordml` | paraId, revision tracking |
| `r:` | `...officeDocument/2006/relationships` | Relaciones (imágenes, hyperlinks) |
| `a:` | `...drawingml/2006/main` | Gráficos y formas |

---

## Integración con el Aldraverse

Este servidor MCP es el **pilar de manipulación documental** del Aldraverse.
Puede conectarse a cualquier proyecto que necesite generar o editar reportes:

- **Anyway** — Generación automática de informes de sesión
- **Séptima** — Reportes de análisis emocional en formato académico
- **Nona** — Exportación de transcripciones de conversación

---

*Construido con 🍒 para el Aldraverse. "Lo que Lupe tomó, el código lo preserva."*
