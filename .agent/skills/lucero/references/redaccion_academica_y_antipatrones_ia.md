# 🎓 PROTOCOLO MAESTRO DE REDACCIÓN ACADÉMICA DE CALIDAD Y PREVENCIÓN DE ANTIPATRONES DE INTELIGENCIA ARTIFICIAL

> **Estatus:** Referencia Normativa Oficial para LUCERO MCP  
> **Alcance:** Documentos DOCX/PDF/MD académicos, protocolos de investigación, proyectos de titulación y reportes técnicos (TecNM / APA 7 / IEEE).  
> **Idioma:** 100% Español Soberano.

---

## 🏛️ PARTE I: CÓMO SE REDACTA UN FORMATO ACADÉMICO DE CALIDAD

La redacción académica formal no es una acumulación de datos o viñetas informativas; es un **sistema de pensamiento crítico estructurado** cuya función primordial es argumentar, justificar y demostrar hallazgos con rigor empírico, claridad analítica y economía lingüística.

---

### 1. PRINCIPIOS RETÓRICOS Y DISCURSIVOS FUNDAMENTALES

#### 1.1 Soberanía de la Prosa Sintagmática (Erradicación del Estilo Diapositiva)
Un documento formal de grado, protocolo o artículo **se escribe en párrafos de prosa continua**.
- **La falacia de la viñeta:** Las viñetas (*bullet points*) pertenecen a diapositivas orales, hojas de especificación rápida o listas de verificación. Fragmentan la lógica discursiva, eluden la demostración de causalidad y destruyen la jerarquía de las ideas.
- **La regla de oro de la prosa técnica:** Todo concepto, requerimiento, resultado o fase metodológica debe desarrollarse mediante párrafos completos donde cada oración cumpla una función:
  1. *Oración temática (Tesis):* Introduce la premisa principal del párrafo.
  2. *Oración de fundamentación (Desarrollo):* Explica el mecanismo, dato empírico o referencia conceptual.
  3. *Oración de impacto o discusión (Consecuencia):* Detalla la implicación técnica o la relación con el objetivo del proyecto.

#### 1.2 Voz Gramatical y Registro Lingüístico
- **Impersonalidad Soberana:** En los manuales de ingeniería, informática y protocolos del TecNM / IEEE, la redacción debe ser impersonal (empleo del pronombre pasivo reflejo *se*):
  - ❌ *"Nosotros desarrollamos una plataforma web para que los alumnos puedan..."*
  - ❌ *"Diseñé una base de datos relacional para guardar..."*
  - ✅ *"Se diseñó una arquitectura de base de datos relacional orientada a preservar la integridad referencial de los expedientes..."*
  - ✅ *"La plataforma web fue implementada bajo el paradigma de microservicios, lo que posibilitó..."*
- **Tiempos Verbales Deterministas:**
  - *Introducción y Planteamiento:* Presente de indicativo (*"El sector de tecnologías de la información presenta una brecha..."*).
  - *Metodología y Procedimientos:* Pasado simple / Pretérito (*"Se administró un cuestionario estructurado a una muestra de 50 egresados..."*).
  - *Resultados:* Pretérito para lo obtenido (*"El análisis arrojó una tasa de desocupación del 72%..."*); presente para verdades comprobadas (*"El modelo confirma la existencia de un punto de equilibrio..."*).
  - *Conclusiones:* Pasado para el trabajo realizado y presente/futuro condicional para prospectivas.

#### 1.3 Conectores Lógicos Interpárrafo e Intrapárrafo
La fluidez de un texto científico descansa en sus enlaces lógicos. Queda prohibido yuxtaponer oraciones simples sin conectores discursivos adecuados:
- **Causalidad / Consecuencia:** *Por consiguiente, en virtud de lo anterior, de este modo, en consecuencia, de ahí que.*
- **Contraste / Objeción:** *No obstante, por el contrario, si bien es cierto que, a pesar de ello, en contraposición.*
- **Adición / Complementariedad:** *Asimismo, por añadidura, en paralelo, de forma análoga, paralelamente.*
- **Transición Temática:** *En lo relativo a, respecto de la dimensión operativa, en el plano financiero.*

---

### 2. ESTRUCTURA Y ANATOMÍA DE LAS SECCIONES ACADÉMICAS

#### 2.1 Justificación y Objetivos
- **Justificación:** Debe responder a tres dimensiones explícitas: *Justificación Teórico-Científica* (qué vacío de conocimiento llena), *Justificación Metodológica/Tecnológica* (qué herramientas o arquitecturas aporta) y *Justificación Social/Institucional* (qué población se beneficia y cómo se mide ese beneficio).
- **Objetivos Específicos:** No son tareas de agenda; son estadios cognitivos y técnicos que sumados resuelven el objetivo general. Se redactan con un solo verbo en infinitivo taxativo (Bloom/Marzano: *Diseñar, Evaluar, Implementar, Cuantificar, Validar*).

#### 2.2 Tratamiento Riguroso de Modelos Matemáticos y Muestreo
- Toda fórmula (e.g., cálculo de muestra finita) debe presentarse en renglón independiente, definiendo formalmente cada parámetro, su valor empírico y la sustitución algebraica paso a paso:
  $$n = \frac{N \cdot Z^2 \cdot p \cdot q}{e^2 \cdot (N - 1) + Z^2 \cdot p \cdot q}$$
- Es inaceptable en una auditoría colocar la fórmula y saltar al resultado sin el paso intermedio de resolución numérica explícita.

#### 2.3 Tratamiento de Tablas y Figuras (Norma APA 7ma / TecNM)
- **Tablas:**
  - Encabezado: `Tabla 1` en negrita, seguido de salto de línea con el nombre de la tabla en cursiva (*Variables demográficas de la población*).
  - Solo 3 líneas horizontales visibles: borde superior de encabezados, borde inferior de encabezados y borde de cierre inferior. Cero líneas verticales divisorias (estilo matriz científica abierta).
  - Pie de tabla: `Nota.` en cursiva seguida de aclaraciones metodológicas, abreviaturas y fuente formal.
- **Figuras y Diagramas:**
  - Todo diagrama de flujo, esquema de layout o captura debe ser legible, vectorizado o de alta resolución (>300 DPI).
  - Prohibido dejar esquemas flotantes sin mención en el texto: todo gráfico debe ser introducido antes de su aparición (*"Como se ilustra en la Figura 3..."*).

---

## 🛑 PARTE II: CATÁLOGO DE ANTIPATRONES DE IA EN DOCUMENTOS ACADÉMICOS

La Inteligencia Artificial generativa presenta sesgos predecibles que erosionan la calidad de un documento científico. Para asegurar que los textos procesados con LUCERO posean calidad humana impecable, se tipifican los siguientes antipatrones:

### 1. Antipatrón: "Bullet-Pointitis" (Hiperfragmentación por Viñetas)
- **El Síntoma:** La IA convierte explicaciones analíticas en listas interminables con un subtítulo en negrita y dos renglones genéricos.
- **El Daño:** Rompe el flujo de lectura; produce un efecto de "presentación PowerPoint copiada en Word" y evade el análisis de interdependencia sistémica.
- **Solución Correctiva (Prosa Continua):** Integrar la información en párrafos sintagmáticos continuos con conectores intra e interpárrafo.

### 2. Antipatrón: "AI Puffery" (Adjetivación Grandilocuente y Falsa Trascendencia)
- **El Síntoma:** Uso recurrente de adjetivos superlativos e hiperbólicos para enmascarar la falta de datos ("revolucionario, crucial, vital, de suma importancia, piedra angular, un faro de innovación, tapiz, fascinante, profundo, indispensable").
- **Solución Correctiva:** Sustituir todo adjetivo vacío por un hecho empírico mensurable (porcentajes, tiempos de respuesta, reducción de costos).

### 3. Antipatrón: "Metronome Rhythm" (Monotonía y Simetría Sintáctica Artificial)
- **El Síntoma:** Todos los párrafos miden exactamente 3 oraciones de 20 palabras con la estructura lineal `[Sujeto + Verbo + Predicado]`.
- **Solución Correctiva:** Alternar deliberadamente oraciones cortas y asertivas con oraciones compuestas subordinadas para generar cadencia natural y riqueza rítmica.

### 4. Antipatrón: "The Floating Statistic" (El Punteo de Porcentajes Huérfanos)
- **El Síntoma:** En la sección de resultados, listar guiones sueltos con porcentajes sin correlación.
- **Solución Correctiva:** Agrupar variables en torno a hipótesis, contrastar con la literatura y explicar el significado cualitativo de la cifra dentro del contexto del proyecto.

### 5. Antipatrón: "Phantom Citations" y Citas Epistémicamente Flotantes
- **El Síntoma:** Inventar fuentes o insertar citas al azar sin relación directa con el dato mencionado.
- **Solución Correctiva:** Solo emplear fuentes académicas oficiales y verificables (TecNM, INEGI, CACEI, CONAHCYT, IEEE) con referencia explícita a la idea parafraseada.

### 6. Antipatrón: "Conclusion Loop" (El Falso Cierre Redundante)
- **El Síntoma:** Iniciar conclusiones con "En conclusión..." y limitarse a repetir el resumen sin aportar síntesis crítica.
- **Solución Correctiva:** Demostrar el cumplimiento de los objetivos planteados, declarar las limitaciones metodológicas y proponer líneas futuras concretas de desarrollo.

---

## 📋 PARTE III: LISTA DE CONTROL (CHECKLIST) PRE-ENTREGA DOCUMENTAL

Antes de dar por finalizado cualquier documento generado o editado con LUCERO, se debe auditar:

- [ ] **1. Cero Viñetas Innecesarias:** ¿Las justificaciones, resultados y características técnicas están redactadas en prosa analítica continua y no en listas de viñetas?
- [ ] **2. Cero AI-Puffery:** ¿Se eliminaron adjetivos grandilocuentes ("revolucionario", "crucial", "piedra angular", "vital")?
- [ ] **3. Desglose Matemático Completo:** ¿Toda ecuación de muestreo o financiera muestra la sustitución numérica de cada variable?
- [ ] **4. Tablas Abiertas APA 7:** ¿Las tablas cuentan únicamente con tres líneas horizontales y carecen de cuadrícula interna cerrada?
- [ ] **5. Conectores Lógicos Activos:** ¿Cada párrafo inicia con una relación discursiva respecto del párrafo anterior?
- [ ] **6. Voz Impersonal Estricta:** ¿Se erradicó el uso de la primera persona ("hicimos", "creamos") y se sustituyó por impersonal ("se diseñó", "se analizó")?
- [ ] **7. Títulos Formales de Gráfico:** ¿Cada figura cuenta con su identificación formal superior o inferior y su correspondiente `Nota.` metodológica?
