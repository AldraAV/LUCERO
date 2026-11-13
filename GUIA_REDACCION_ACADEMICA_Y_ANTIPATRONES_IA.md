# 🎓 PROTOCOLO MAESTRO DE REDACCIÓN ACADÉMICA DE CALIDAD Y PREVENCIÓN DE ANTIPATRONES DE INTELIGENCIA ARTIFICIAL

> **Estatus:** Guía Normativa y Manual de Operación para LUCERO MCP y Agentes del Ecosistema  
> **Alcance:** Documentación técnica, tesis de titulación, protocolos de investigación, artículos científicos y reportes de ingeniería (TecNM / APA 7 / IEEE).  
> **Idioma:** 100% Español Soberano. Prohibición estricta de emojis en bloques de código o sintaxis técnica.

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

```
        ┌─────────────────────────────────────────────────────────┐
        │                 DOCUMENTO ACADÉMICO                     │
        └────────────────────────────┬────────────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│  PLANTEAMIENTO   │       │   METODOLOGÍA    │       │    DISCUSIÓN     │
│   Y PROBLEMA     │       │   Y TÉCNICA      │       │  Y RESULTADOS    │
├──────────────────┤       ├──────────────────┤       ├──────────────────┤
│• Contexto real   │       │• Operacionaliza- │       │• Narrativa con   │
│• Cero adjetivos  │       │  ción precisa    │       │  porcentajes     │
│• Evidencia dura  │       │• Fórmulas paso   │       │• Contraste con   │
│• Pregunta rectora│       │  a paso explícit.│       │  marco teórico   │
└──────────────────┘       └──────────────────┘       └──────────────────┘
```

#### 2.1 Justificación y Objetivos
- **Justificación:** Debe responder a tres dimensiones explícitas: *Justificación Teórico-Científica* (qué vacío de conocimiento llena), *Justificación Metodológica/Tecnológica* (qué herramientas o arquitecturas aporta) y *Justificación Social/Institucional* (qué población se beneficia y cómo se mide ese beneficio).
- **Objetivos Específicos:** No son tareas de agenda (e.g. *"Reunirse con el comité"*); son estadios cognitivos y técnicos que sumados resuelven el objetivo general. Se redactan con un solo verbo en infinitivo taxativo (Bloom/Taxonomía de Marzano: *Diseñar, Evaluar, Implementar, Cuantificar, Validar*).

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

La Inteligencia Artificial generativa presenta sesgos predecibles que erosionan la calidad de un documento científico. Para asegurar que los textos procesados con LUCERO posean calidad humana impecable, se tipifican los siguientes 10 antipatrones:

---

### 1. Antipatrón: "Bullet-Pointitis" (Hiperfragmentación por Viñetas)
- **El Síntoma:** La IA convierte explicaciones analíticas en listas interminables con un subtítulo en negrita y dos renglones genéricos:
  ```
  ❌ DEFICIENTE (Generación IA genérica):
  * Módulo de egresados: Permite construir un perfil profesional sumamente completo con GitHub.
  * Módulo empresarial: Facilita a las empresas publicar vacantes orientadas a TIC.
  * Módulo institucional: Incorpora paneles administrativos con gráficas en tiempo real.
  ```
- **El Daño:** Rompe el flujo de lectura; produce un efecto de "presentación PowerPoint copiada en Word" y evade el análisis de interdependencia sistémica.
- **Solución Correctiva (Prosa Continua):**
  ```
  ✅ PROSA ACADÉMICA DE CALIDAD:
  La arquitectura funcional del sistema se estructura en tres componentes interconectados. En primera instancia, el módulo de egresados centraliza la trayectoria profesional del profesionista mediante repositorios de código verificables y certificaciones técnicas. Dicha información alimenta de manera síncrona el subsistema empresarial, permitiendo que las organizaciones publiquen ofertas laborales con algoritmos de filtrado adaptados a los perfiles de tecnologías de la información. Por último, la información transaccional generada por ambas partes converge en un panel analítico institucional, el cual suministra métricas de inserción laboral en tiempo real para las autoridades académicas.
  ```

---

### 2. Antipatrón: "AI Puffery" (Adjetivación Grandilocuente y Falsa Trascendencia)
- **El Síntoma:** Uso recurrente de adjetivos superlativos e hiperbólicos para enmascarar la falta de datos:
  - *Vocabulario delator de IA:* "revolucionario, crucial, vital, de suma importancia, piedra angular, un faro de innovación, testimonio de, tapiz, fascinante, profundo, indispensable, sin lugar a dudas".
- **El Daño:** En ciencia e ingeniería no existen soluciones "revolucionarias" por decreto; la eficacia se demuestra con métricas de rendimiento, ahorro de tiempo o tasas de reducción de error.
- **Solución Correctiva:** Sustituir todo adjetivo vacío por un hecho empírico mensurable.
  - ❌ *"EmpleaTEC representa una revolución crucial que cambiará para siempre el destino de los graduados..."*
  - ✅ *"La implementación de EmpleaTEC reduce en un 65% el tiempo promedio de colocación laboral en comparación con las bolsas de trabajo manuales..."*

---

### 3. Antipatrón: "Metronome Rhythm" (Monotonía y Simetría Sintáctica Artificial)
- **El Síntoma:** Todos los párrafos miden exactamente 3 oraciones. Cada oración tiene entre 18 y 22 palabras. Todas siguen la estructura lineal idéntica: `[Sujeto + Verbo + Predicado + Conector + Conclusión]`.
- **El Daño:** La lectura resulta robótica, carente de dinamismo intelectual y sumamente cansina para revisores y comités de arbitraje.
- **Solución Correctiva (Cadencia Natural y Ráfagas de Variabilidad):** Alternar deliberadamente oraciones cortas y asertivas con oraciones compuestas subordinadas:
  - *"El resultado fue contundente. Mientras que el 72% de los encuestados reportó dificultades severas para acceder a su primer empleo tecnológico debido a la falta de experiencia formal, únicamente el 26% tuvo acceso a programas de residencias coordinados con empresas del sector durante su formación escolar."*

---

### 4. Antipatrón: "The Floating Statistic" (El Punteo de Porcentajes Huérfanos)
- **El Síntoma:** En la sección de resultados, la IA escribe:
  - *- El 72% dijo que sí.*
  - *- El 70% considera que el plan está desactualizado.*
  - *- El 76% no tiene experiencia.*
- **El Daño:** Eso no es análisis; es una transcripción floja de una hoja de cálculo. En una investigación se requiere **triangulación de variables**.
- **Solución Correctiva:** Agrupar variables en torno a hipótesis y explicar la correlación:
  - *"Al correlacionar la percepción de saturación laboral (72%) con el desajuste curricular percibido (70%), se evidencia que la resistencia para acceder al mercado laboral no radica en la escasez de vacantes, sino en la discrepancia cualitativa entre el perfil de egreso y las tecnologías demandadas por los reclutadores."*

---

### 5. Antipatrón: "Phantom Citations" y Citas Epistémicamente Flotantes
- **El Síntoma:** La IA inventa referencias bibliográficas que suenan plausibles pero no existen, o inserta citas al azar al final de párrafos para aparentar respaldo ("(García, 2021)") sin haber parafraseado ninguna idea específica de ese autor.
- **Solución Correctiva:**
  - Solo incluir fuentes verificadas en bases de datos científicas reales (Scopus, SciELO, Redalyc, IEEE Xplore, Google Scholar, INEGI).
  - Toda cita debe atribuir un método, un hallazgo o una teoría puntual, nunca una obviedad.

---

### 6. Antipatrón: "Conclusion Loop" (El Falso Cierre Redundante)
- **El Síntoma:** Conclusiones que abren con: *"En conclusión...", "En resumen...", "A lo largo de este trabajo se demostró que..."* y proceden a repetir palabra por palabra las oraciones del Resumen y de la Introducción.
- **El Daño:** Demuestra incapacidad de síntesis de alto nivel y falta de autocrítica técnica.
- **Solución Correctiva:** Una conclusión de calidad debe abordar tres elementos indispensables:
  1. *Comprobación o refutación de la hipótesis/objetivo inicial.*
  2. *Limitaciones metodológicas encontradas durante el desarrollo.*
  3. *Líneas futuras de investigación y escalabilidad tecnológica.*

---

### 7. Antipatrón: "Nominalization Swelling" (Hinchazón por Nominalización)
- **El Síntoma:** Reemplazar verbos directos y dinámicos por secuencias complejas de sustantivos abstractos:
  - ❌ *"Se llevó a cabo la realización de la verificación de la autenticación de los datos..."* (3 nominalizaciones sucesivas).
  - ✅ *"Se verificaron las credenciales de los usuarios mediante algoritmos de hashing..."*

---

### 8. Antipatrón: "The Sycophantic Balance" (Falsa Neutralidad Evasiva)
- **El Síntoma:** La IA evita asumir una postura técnica concluyente: *"Existen ventajas y desventajas en ambas bases de datos, por lo que la elección dependerá de cada usuario."*
- **El Daño:** En ingeniería de proyectos se debe justificar una decisión técnica concreta y fundamentada.
- **Solución Correctiva:** Tomar postura fundamentada:
  - *"Se seleccionó PostgreSQL sobre bases de datos no relacionales debido a la estricta necesidad de mantener integridad transaccional ACID en el registro de convocatorias y postulaciones empresariales."*

---

## 🛠️ PARTE III: MATRIZ DE TRANSFORMACIÓN ANTES / DESPUÉS

| Caso de Uso | Texto Generado por IA Deficiente (Rechazado) | Redacción Académica Rigurosa (Aprobado LUCERO) |
| :--- | :--- | :--- |
| **Justificación de Proyecto** | *"Este proyecto es una piedra angular indispensable que revolucionará la forma en que los alumnos se conectan con el mundo laboral, facilitando un sinfín de oportunidades."* | *"La relevancia del proyecto estriba en su capacidad para reducir la asimetría informativa entre las competencias curriculares del ITSNa y los requerimientos del sector productivo regional."* |
| **Resultados de Encuesta** | *"- 76% no tiene experiencia.<br>- 50% dice que la práctica es poca.<br>- 84% pide vinculación urgente."* | *"Los hallazgos del instrumento diagnóstico reflejan una barrera estructural de entrada: el 76% de los egresados atribuye su desempleo inicial a la falta de experiencia laboral previa, fenómeno estrechamente ligado a que la mitad de la muestra (50%) califica su entrenamiento práctico institucional como insuficiente. En respuesta a ello, el 84% de los participantes enfatiza la urgencia de establecer mecanismos formales de vinculación desde semestres intermedios."* |
| **Descripción de Infraestructura** | *"- Servidor: AWS para estar en la nube.<br>- Dominio: .edu.mx para que sea de escuela.<br>- Seguridad: HTTPS para que nadie robe datos."* | *"La plataforma opera sobre una arquitectura en la nube aprovisionada en Amazon Web Services (AWS), lo que garantiza una disponibilidad del 99.9% y elasticidad ante incrementos estacionales de tráfico. El acceso se autentica mediante certificados SSL/TLS con cifrado de grado militar sobre protocolo HTTPS, resguardando la confidencialidad de la información conforme a la Ley Federal de Protección de Datos Personales en Posesión de los Particulares (LFPDPPP)."* |

---

## 📋 PARTE IV: LISTA DE CONTROL (CHECKLIST) PRE-ENTREGA DOCUMENTAL

Antes de dar por finalizado cualquier documento generado o editado con LUCERO, se debe auditar:

- [ ] **1. Cero Viñetas Innecesarias:** ¿Las justificaciones, resultados y características técnicas están redactadas en prosa analítica continua y no en listas de viñetas?
- [ ] **2. Cero AI-Puffery:** ¿Se eliminaron adjetivos grandilocuentes ("revolucionario", "crucial", "piedra angular", "vital")?
- [ ] **3. Desglose Matemático Completo:** ¿Toda ecuación de muestreo o financiera muestra la sustitución numérica de cada variable?
- [ ] **4. Tablas Abiertas APA 7:** ¿Las tablas cuentan únicamente con tres líneas horizontales y carecen de cuadrícula interna cerrada?
- [ ] **5. Conectores Lógicos Activos:** ¿Cada párrafo inicia con una relación discursiva respecto del párrafo anterior?
- [ ] **6. Voz Impersonal Estricta:** ¿Se erradicó el uso de la primera persona ("hicimos", "creamos") y se sustituyó por impersonal ("se diseñó", "se analizó")?
- [ ] **7. Títulos Formales de Gráfico:** ¿Cada figura cuenta con su identificación formal superior o inferior y su correspondiente `Nota.` metodológica?
- [ ] **8. Cero Emojis en Código y Documentos:** ¿Se verificó la total ausencia de caracteres especiales emoji?
