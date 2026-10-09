# Normativas de Formato Estricto - APA 7ma Edición (Adaptación OOXML para LUCERO)

Este archivo define los invariables arquitectónicos y de estilo que LUCERO debe aplicar y reconocer al generar, modificar o auditar documentos `.docx`. Queda estrictamente prohibido el uso de estilos paliativos o adivinar formatos.

## 1. Tipografía y Fuentes Permitidas
- **Fuentes Sans Serif**: Calibri (11 pts), Arial (11 pts), Lucida Sans Unicode (10 pts).
- **Fuentes Serif**: Times New Roman (12 pts), Georgia (11 pts).
- **Consistencia**: El documento debe utilizar la misma fuente en todo el texto (excepto código fuente: Courier 10 pts).

## 2. Espaciado y Márgenes
- **Márgenes**: 1 pulgada (2.54 cm) en todos los lados.
- **Interlineado**: Doble espacio (2.0) obligatorio en TODO el documento (incluyendo listas, citas y notas), sin agregar espacios adicionales antes o después de los párrafos.
- **Alineación**: Izquierda (ragged right), sin justificar.
- **Sangría**: Primera línea de cada párrafo estándar con sangría de 0.5 pulgadas (1.27 cm).

## 3. Jerarquía de Títulos (Headings)
LUCERO debe estructurar los nodos `<w:pStyle>` o `<w:rPr>` acatando exactamente estos 5 niveles. No se deben usar números ni letras para identificarlos.
- **Nivel 1**: Centrado, **Negrita**, Cada Palabra Principal Con Mayúscula. (El texto comienza en un nuevo párrafo).
- **Nivel 2**: Alineado a la izquierda, **Negrita**, Cada Palabra Principal Con Mayúscula. (El texto comienza en un nuevo párrafo).
- **Nivel 3**: Alineado a la izquierda, **Negrita**, ***Cursiva***, Cada Palabra Principal Con Mayúscula. (El texto comienza en un nuevo párrafo).
- **Nivel 4**: Sangría de 0.5 pulg. (1.27 cm), **Negrita**, Cada Palabra Principal Con Mayúscula, finaliza con un punto. (El texto continúa inmediatamente en la misma línea).
- **Nivel 5**: Sangría de 0.5 pulg. (1.27 cm), **Negrita**, ***Cursiva***, Cada Palabra Principal Con Mayúscula, finaliza con un punto. (El texto continúa inmediatamente en la misma línea).

## 4. Listas y Viñetas (List Paragraphs)
LUCERO debe parsear o inyectar las listas respetando el interlineado doble y la sangría correspondiente:
- **Listas con Viñetas (Bullets)**: Usar cuando el orden de los elementos no importa. La viñeta debe tener sangría de 0.5 pulgadas (1.27 cm) desde el margen izquierdo, y el texto debe tener sangría francesa (hanging indent) a 1 pulgada.
- **Listas Numeradas**: Usar cuando los elementos siguen un orden jerárquico o secuencial estricto (ej. 1, 2, 3). Misma regla de sangría que las viñetas.
- **Listas con Letras**: (a), (b), (c)... Se utilizan para separar elementos *dentro* de un párrafo continuo sin romperlo en múltiples líneas (seriación en párrafo).

## 5. Figuras, Tablas y Gráficos (El Eje Espacial)
1. **Número de la Figura**: (Ej. "**Figura 1**"). Alineado a la izquierda, en **negrita**.
2. **Título de la Figura**: En la línea siguiente al número. Alineado a la izquierda, en *cursiva*, con Cada Palabra Principal en Mayúscula. (Interlineado doble).
3. **El Gráfico / Imagen**: Insertado sin contornos, dimensiones respetadas (sin logo aplastado).
4. **Nota de la Figura**: Debajo de la imagen. Inicia con "*Nota.*" (en cursiva y con punto), seguido de la explicación en fuente normal, interlineado doble.
