# LUCERO (Décimo Hermano) - Servidor MCP de Cirugía Quirúrgica de Documentos

LUCERO opera sobre los tres formatos estándar de la ofimática moderna (**DOCX, PPTX y XLSX**), interactuando directamente a nivel OOXML (ECMA-376) y árboles XML para garantizar el principio inquebrantable de **ZERO FORMAT LOSS** (cero pérdida de estilos, fuentes, márgenes o fórmulas).

---

## 🏛️ 1. Matriz de Capacidades y Herramientas

### A. Documentos de Texto (.docx)
* `inspect_xml_tree`: Inspecciona la jerarquía y nodos XML del documento.
* `run_xpath`: Ejecuta consultas XPath 1.0 sobre cualquier archivo XML del paquete (`word/document.xml`, `comments`, etc.).
* `surgical_replace`: Sustituye texto de forma atómica en nodos de texto (`<w:t>`) sin romper runs ni estilos.
* `inject_apa_structure`: Inyecta bloques de estructura formal APA 7ª (`figure_label`, `figure_note`, `body_paragraph`, `heading1-5`, `reference`).
* `surgical_inject_image` / `surgical_replace_image`: Inyecta o sustituye imágenes con calibración en pulgadas y preservación de relaciones (`rId`).
* `commit_changes`: Guarda y reempaqueta el archivo OOXML de forma limpia y validada.

### B. Hojas de Cálculo (.xlsx) - Motor de Curación de Datos
* `inspect_excel_sheets`: Mapea las hojas, dimensiones, celdas ocupadas, rangos combinados y tablas estructuradas.
* `inspect_excel_cells`: Inspecciona cuadrantes matriciales extrayendo valor real, fórmula matemática y metadatos de estilo.
* `surgical_replace_excel_cell`: Modifica atómicamente una celda preservando bordes, fuentes y alineación original.
* `surgical_inject_excel_table`: Inyecta tablas completas o diccionarios `clave: valor` con autoajuste de anchos de columna y preservación de fórmulas adyacentes.
* `surgical_search_replace_excel`: Búsqueda y reemplazo global en una o todas las hojas del libro sin corromper fórmulas.

### C. Presentaciones (.pptx)
* `pptx_inspect_slides`: Inspecciona diapositivas, textos y figuras.
* `pptx_surgical_replace`: Reemplazo de texto atómico en diapositivas.
* `pptx_inject_image`: Inserción de imágenes con cálculo exacto de posición EMU.
* `pptx_compile_from_svg`: Ensamblaje de diapositivas vectoriales.

---

## 🧭 2. Protocolo de Curación y Limpieza de Datos en Excel

Al auditar, barrer o reconciliar libros contables y financieros complejos:

```
1. MAPEAR HOJAS         → inspect_excel_sheets(excel_path)
2. EXTRAER CUADRANTE    → inspect_excel_cells(excel_path, sheet_name, cell_range="A1:M60")
3. AUDITAR FÓRMULAS     → Verificar que las celdas calculadas (=SUMA, etc.) no sean sobreescritas con texto fijo.
4. INYECCIÓN ATÓMICA    → surgical_inject_excel_table() para matrices o surgical_replace_excel_cell() para celdas clave.
5. VALIDACIÓN FINAL     → Reinspeccionar celdas para confirmar concordancia de totales y balances.
```

---

## 🧹 3. Protocolo de Desresaltado y Limpieza de Revisiones en DOCX

1. Buscar marcas de resaltado: `run_xpath(docx_path, xpath_expr="//w:highlight")`.
2. Remover los nodos `<w:highlight>` de todos los runs afectados.
3. Verificar conteo residual: `0` resaltados garantizan la entrega limpia a la docente o cliente.
