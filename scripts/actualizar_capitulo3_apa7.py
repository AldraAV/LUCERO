"""
actualizar_capitulo3_apa7.py — Script oficial de reestructuracion academica APA 7.
Aplica transformaciones de precision quirurgica con DocxSurgeon:
1. Desplaza indices de tablas subsecuentes (Tabla 12 -> 13, 11 -> 12, 10 -> 11, 9 -> 10).
2. Re-calibra Tabla 8 (Requerimientos de Infraestructura) a nivel ingenieril superior (10pt, 2800/6500 dxa).
3. Inyecta Tabla 9 (Matriz de Proveedores y Disponibilidad) formal en Seccion 3.2.
4. Homogeneiza el interlineado estricto (cuerpo 2.0 / tablas 1.0) en todo el documento.
"""
from __future__ import annotations

import sys
import shutil
from pathlib import Path
from lxml import etree

# Agregar raiz de LUCERO al sys.path
raiz_lucero = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(raiz_lucero))

from src.surgeon import DocxSurgeon
from src.utils import NS, qn

def crear_run_texto(texto: str, negrita: bool = False, cursiva: bool = False, tamano_medio_punto: int = 20) -> etree._Element:
    """Crea un nodo w:r con tipografia Times New Roman y formato especifico."""
    run = etree.Element(qn("w", "r"))
    rpr = etree.SubElement(run, qn("w", "rPr"))

    rfonts = etree.SubElement(rpr, qn("w", "rFonts"))
    rfonts.set(qn("w", "ascii"), "Times New Roman")
    rfonts.set(qn("w", "hAnsi"), "Times New Roman")
    rfonts.set(qn("w", "cs"), "Times New Roman")

    if negrita:
        etree.SubElement(rpr, qn("w", "b"))
        etree.SubElement(rpr, qn("w", "bCs"))
    if cursiva:
        etree.SubElement(rpr, qn("w", "i"))
        etree.SubElement(rpr, qn("w", "iCs"))

    sz = etree.SubElement(rpr, qn("w", "sz"))
    sz.set(qn("w", "val"), str(tamano_medio_punto))
    sz_cs = etree.SubElement(rpr, qn("w", "szCs"))
    sz_cs.set(qn("w", "val"), str(tamano_medio_punto))

    t_node = etree.SubElement(run, qn("w", "t"))
    t_node.text = texto
    if texto.startswith(" ") or texto.endswith(" "):
        t_node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    return run

def crear_parrafo_cuerpo(texto: str) -> etree._Element:
    """Crea un parrafo de cuerpo APA 7: Times New Roman 12pt, interlineado doble (480), sangria 720."""
    p = etree.Element(qn("w", "p"))
    ppr = etree.SubElement(p, qn("w", "pPr"))

    pstyle = etree.SubElement(ppr, qn("w", "pStyle"))
    pstyle.set(qn("w", "val"), "Normal")

    espaciado = etree.SubElement(ppr, qn("w", "spacing"))
    espaciado.set(qn("w", "line"), "480")
    espaciado.set(qn("w", "lineRule"), "auto")
    espaciado.set(qn("w", "before"), "0")
    espaciado.set(qn("w", "after"), "0")

    ind = etree.SubElement(ppr, qn("w", "ind"))
    ind.set(qn("w", "firstLine"), "720")

    jc = etree.SubElement(ppr, qn("w", "jc"))
    jc.set(qn("w", "val"), "left")

    p.append(crear_run_texto(texto, tamano_medio_punto=24))
    return p

def crear_etiqueta_tabla(numero_tabla: int, titulo: str) -> list[etree._Element]:
    """Genera las dos lineas de etiqueta APA 7 para una tabla: 'Tabla N' (negrita) y Titulo (cursiva)."""
    p_num = etree.Element(qn("w", "p"))
    ppr1 = etree.SubElement(p_num, qn("w", "pPr"))
    ind1 = etree.SubElement(ppr1, qn("w", "ind"))
    ind1.set(qn("w", "firstLine"), "0")
    esp1 = etree.SubElement(ppr1, qn("w", "spacing"))
    esp1.set(qn("w", "line"), "240")
    esp1.set(qn("w", "lineRule"), "auto")
    esp1.set(qn("w", "before"), "120")
    esp1.set(qn("w", "after"), "0")
    p_num.append(crear_run_texto(f"Tabla {numero_tabla}", negrita=True, tamano_medio_punto=20))

    p_tit = etree.Element(qn("w", "p"))
    ppr2 = etree.SubElement(p_tit, qn("w", "pPr"))
    ind2 = etree.SubElement(ppr2, qn("w", "ind"))
    ind2.set(qn("w", "firstLine"), "0")
    esp2 = etree.SubElement(ppr2, qn("w", "spacing"))
    esp2.set(qn("w", "line"), "240")
    esp2.set(qn("w", "lineRule"), "auto")
    esp2.set(qn("w", "before"), "0")
    esp2.set(qn("w", "after"), "60")
    p_tit.append(crear_run_texto(titulo, cursiva=True, tamano_medio_punto=20))

    return [p_num, p_tit]

def crear_nota_tabla(texto_nota: str) -> etree._Element:
    """Genera el parrafo formal de nota APA 7: 'Nota.' en cursiva mas texto explicativo."""
    p = etree.Element(qn("w", "p"))
    ppr = etree.SubElement(p, qn("w", "pPr"))
    ind = etree.SubElement(ppr, qn("w", "ind"))
    ind.set(qn("w", "firstLine"), "0")
    esp = etree.SubElement(ppr, qn("w", "spacing"))
    esp.set(qn("w", "line"), "240")
    esp.set(qn("w", "lineRule"), "auto")
    esp.set(qn("w", "before"), "60")
    esp.set(qn("w", "after"), "180")
    p.append(crear_run_texto("Nota. ", cursiva=True, tamano_medio_punto=19))
    p.append(crear_run_texto(texto_nota, tamano_medio_punto=19))
    return p

def construir_tabla_ooxml(encabezados: list[str], filas_datos: list[list[str]], anchos_col: list[int]) -> etree._Element:
    """Construye un elemento w:tbl nativo con estilo APA 7 (bordes horizontales limpios y tipografia 10pt)."""
    tbl = etree.Element(qn("w", "tbl"))

    # 1. tblPr
    tblPr = etree.SubElement(tbl, qn("w", "tblPr"))
    tblStyle = etree.SubElement(tblPr, qn("w", "tblStyle"))
    tblStyle.set(qn("w", "val"), "Tablaconcuadrcula")

    ancho_total = sum(anchos_col)
    tblW = etree.SubElement(tblPr, qn("w", "tblW"))
    tblW.set(qn("w", "w"), str(ancho_total))
    tblW.set(qn("w", "type"), "dxa")

    tblLayout = etree.SubElement(tblPr, qn("w", "tblLayout"))
    tblLayout.set(qn("w", "type"), "fixed")

    # Bordes segun APA 7: superior (6), inferior (6), encabezado inferior (6), verticales ninguno
    tblBorders = etree.SubElement(tblPr, qn("w", "tblBorders"))
    for b_name in ["top", "bottom"]:
        b_elem = etree.SubElement(tblBorders, qn("w", b_name))
        b_elem.set(qn("w", "val"), "single")
        b_elem.set(qn("w", "sz"), "6")
        b_elem.set(qn("w", "space"), "0")
        b_elem.set(qn("w", "color"), "000000")

    for b_name in ["left", "right", "insideV"]:
        b_elem = etree.SubElement(tblBorders, qn("w", b_name))
        b_elem.set(qn("w", "val"), "none")

    insideH = etree.SubElement(tblBorders, qn("w", "insideH"))
    insideH.set(qn("w", "val"), "single")
    insideH.set(qn("w", "sz"), "4")
    insideH.set(qn("w", "space"), "0")
    insideH.set(qn("w", "color"), "D3D3D3")

    # 2. tblGrid
    tblGrid = etree.SubElement(tbl, qn("w", "tblGrid"))
    for w in anchos_col:
        col = etree.SubElement(tblGrid, qn("w", "gridCol"))
        col.set(qn("w", "w"), str(w))

    # 3. Fila de Encabezados
    tr_header = etree.SubElement(tbl, qn("w", "tr"))
    trPr = etree.SubElement(tr_header, qn("w", "trPr"))
    etree.SubElement(trPr, qn("w", "tblHeader"))

    for idx, enc in enumerate(encabezados):
        tc = etree.SubElement(tr_header, qn("w", "tc"))
        tcPr = etree.SubElement(tc, qn("w", "tcPr"))
        tcW = etree.SubElement(tcPr, qn("w", "tcW"))
        tcW.set(qn("w", "w"), str(anchos_col[idx]))
        tcW.set(qn("w", "type"), "dxa")

        # Borde inferior del encabezado mas marcado
        tcBorders = etree.SubElement(tcPr, qn("w", "tcBorders"))
        bot = etree.SubElement(tcBorders, qn("w", "bottom"))
        bot.set(qn("w", "val"), "single")
        bot.set(qn("w", "sz"), "6")
        bot.set(qn("w", "space"), "0")
        bot.set(qn("w", "color"), "000000")

        # Shading suave de cabecera
        shd = etree.SubElement(tcPr, qn("w", "shd"))
        shd.set(qn("w", "val"), "clear")
        shd.set(qn("w", "color"), "auto")
        shd.set(qn("w", "fill"), "F1F5F9")

        p = etree.SubElement(tc, qn("w", "p"))
        ppr = etree.SubElement(p, qn("w", "pPr"))
        jc = etree.SubElement(ppr, qn("w", "jc"))
        jc.set(qn("w", "val"), "center" if idx > 0 else "left")
        esp = etree.SubElement(ppr, qn("w", "spacing"))
        esp.set(qn("w", "line"), "240")
        esp.set(qn("w", "lineRule"), "auto")
        esp.set(qn("w", "before"), "80")
        esp.set(qn("w", "after"), "80")
        ind = etree.SubElement(ppr, qn("w", "ind"))
        ind.set(qn("w", "firstLine"), "0")

        p.append(crear_run_texto(enc, negrita=True, tamano_medio_punto=20))

    # 4. Filas de Datos
    for fila in filas_datos:
        tr = etree.SubElement(tbl, qn("w", "tr"))
        for idx, valor in enumerate(fila):
            tc = etree.SubElement(tr, qn("w", "tc"))
            tcPr = etree.SubElement(tc, qn("w", "tcPr"))
            tcW = etree.SubElement(tcPr, qn("w", "tcW"))
            tcW.set(qn("w", "w"), str(anchos_col[idx]))
            tcW.set(qn("w", "type"), "dxa")

            p = etree.SubElement(tc, qn("w", "p"))
            ppr = etree.SubElement(p, qn("w", "pPr"))
            jc = etree.SubElement(ppr, qn("w", "jc"))
            jc.set(qn("w", "val"), "left")
            esp = etree.SubElement(ppr, qn("w", "spacing"))
            esp.set(qn("w", "line"), "240")
            esp.set(qn("w", "lineRule"), "auto")
            esp.set(qn("w", "before"), "60")
            esp.set(qn("w", "after"), "60")
            ind = etree.SubElement(ppr, qn("w", "ind"))
            ind.set(qn("w", "firstLine"), "0")

            es_primera_columna = (idx == 0)
            p.append(crear_run_texto(valor, negrita=es_primera_columna, tamano_medio_punto=20))

    return tbl

def procesar_documento(ruta_docx: Path):
    print(f"=== Procesando con DocxSurgeon: {ruta_docx.name} ===")
    ruta_bak = ruta_docx.with_suffix(ruta_docx.suffix + ".bak")
    if ruta_bak.exists():
        print(f"Restaurando estado prístino desde: {ruta_bak.name}")
        shutil.copyfile(ruta_bak, ruta_docx)
    cirujano = DocxSurgeon(ruta_docx)

    # ─────────────────────────────────────────────────────────────────────────
    # 1. RE-NUMERACIÓN DE TABLAS SUBSECUENTES (Shift +1) ANTES DE INYECTAR TABLA 9
    # ─────────────────────────────────────────────────────────────────────────
    reemplazos_tablas = [
        ("Tabla 12", "Tabla 13"),
        ("Tabla 11", "Tabla 12"),
        ("Tabla 10", "Tabla 11"),
        ("Tabla 9", "Tabla 10"),
    ]

    for objetivo, sustituto in reemplazos_tablas:
        nodos_texto = cirujano.find_by_xpath(f"//w:t[contains(., '{objetivo}')]")
        for t_nodo in nodos_texto:
            txt = t_nodo.text or ""
            t_nodo.text = txt.replace(objetivo, sustituto)
            cirujano._dirty = True
            print(f"Renumerada {objetivo} -> {sustituto}")

    # ─────────────────────────────────────────────────────────────────────────
    # 2. ACTUALIZAR Y OPTIMIZAR TABLA 8 (Requerimientos de Infraestructura)
    # ─────────────────────────────────────────────────────────────────────────
    datos_t8 = [
        ("Servidor Web y Cómputo Cloud", "Servidor Virtual Privado (VPS) en AWS EC2 (instancia t4g.medium con arquitectura Graviton3, 2 vCPU a 2.6 GHz, 4 GB de memoria RAM DDR5 y 50 GB de almacenamiento SSD NVMe redundante). Alojamiento principal de la aplicación con balanceo elástico de carga (ALB) y disponibilidad garantizada del 99.95% de tiempo de actividad."),
        ("Base de Datos Relacional y Almacenamiento", "Clúster gestionado PostgreSQL versión 16 implementado en Supabase Cloud / AWS RDS, con cifrado nativo en reposo bajo estándar AES-256 y respaldos automáticos diarios. Capacidad inicial estimada para 100,000 registros transaccionales con retención de copias de seguridad por 30 días."),
        ("Capa Lógica y Backend API", "Entorno de ejecución en Node.js v20 LTS y TypeScript estructurado bajo Clean Architecture (arquitectura hexagonal) con framework Express / Fastify, validación de esquemas con Zod y documentación de endpoints vía OpenAPI / Swagger."),
        ("Capa de Presentación y Frontend", "Aplicación web construida con Next.js 14 y React 18, implementando renderizado del lado del servidor (SSR) para indexación pública y Client Components con TailwindCSS. Interfaz de usuario altamente responsiva con tiempo de primer contenido visual (FCP) menor a 1.2 segundos."),
        ("Seguridad Perimetral y Certificación SSL", "Certificado digital de cifrado TLS/SSL de 256 bits emitido automáticamente por Let's Encrypt / Cloudflare Edge, complementado con cortafuegos de aplicaciones web (WAF) contra ataques DDoS y políticas estrictas HSTS.")
    ]

    tablas_t8 = cirujano.find_by_xpath("//w:tbl[.//w:t[contains(., 'Servidor') or contains(., 'Infraestructura Tecnológica') or contains(., 'Base de Datos')]]")
    if tablas_t8:
        tbl8 = tablas_t8[0]
        anchos_t8 = [2800, 6500]  # Total: 9300 dxa (6.45 pulgadas)
        tbl_grid = tbl8.find(qn("w", "tblGrid"))
        if tbl_grid is not None:
            for gc in list(tbl_grid.findall(qn("w", "gridCol"))):
                tbl_grid.remove(gc)
            for w_col in anchos_t8:
                gc = etree.SubElement(tbl_grid, qn("w", "gridCol"))
                gc.set(qn("w", "w"), str(w_col))

        filas = tbl8.findall(f".//{qn('w', 'tr')}")
        for f_idx, fila in enumerate(filas):
            celdas = fila.findall(f".//{qn('w', 'tc')}")
            for c_idx, celda in enumerate(celdas):
                if c_idx < len(anchos_t8):
                    tcPr = celda.find(qn("w", "tcPr"))
                    if tcPr is None:
                        tcPr = etree.Element(qn("w", "tcPr"))
                        celda.insert(0, tcPr)
                    tcW = tcPr.find(qn("w", "tcW"))
                    if tcW is None:
                        tcW = etree.SubElement(tcPr, qn("w", "tcW"))
                    tcW.set(qn("w", "w"), str(anchos_t8[c_idx]))
                    tcW.set(qn("w", "type"), "dxa")

                # Si es fila de datos (f_idx >= 1), asegurar textos completos
                if f_idx >= 1 and (f_idx - 1) < len(datos_t8):
                    componente_txt, spec_txt = datos_t8[f_idx - 1]
                    if c_idx == 0:
                        # Limpiar parrafos anteriores y colocar texto estructurado
                        for p_ant in celda.findall(f".//{qn('w', 'p')}"):
                            celda.remove(p_ant)
                        p_nuevo = etree.SubElement(celda, qn("w", "p"))
                        p_nuevo.append(crear_run_texto(componente_txt, negrita=True, tamano_medio_punto=20))
                    elif c_idx == 1:
                        for p_ant in celda.findall(f".//{qn('w', 'p')}"):
                            celda.remove(p_ant)
                        p_nuevo = etree.SubElement(celda, qn("w", "p"))
                        p_nuevo.append(crear_run_texto(spec_txt, negrita=False, tamano_medio_punto=20))

                # Calibrar espaciado e interlineado en los parrafos de la celda
                for p in celda.findall(f".//{qn('w', 'p')}"):
                    ppr = p.find(qn("w", "pPr"))
                    if ppr is None:
                        ppr = etree.Element(qn("w", "pPr"))
                        p.insert(0, ppr)
                    esp = ppr.find(qn("w", "spacing"))
                    if esp is None:
                        esp = etree.SubElement(ppr, qn("w", "spacing"))
                    esp.set(qn("w", "line"), "240")
                    esp.set(qn("w", "lineRule"), "auto")
                    esp.set(qn("w", "before"), "60")
                    esp.set(qn("w", "after"), "60")

                    ind = ppr.find(qn("w", "ind"))
                    if ind is None:
                        ind = etree.SubElement(ppr, qn("w", "ind"))
                    ind.set(qn("w", "firstLine"), "0")

                    for r in p.findall(f".//{qn('w', 'r')}"):
                        rpr = r.find(qn("w", "rPr"))
                        if rpr is None:
                            rpr = etree.Element(qn("w", "rPr"))
                            r.insert(0, rpr)
                        rfonts = rpr.find(qn("w", "rFonts"))
                        if rfonts is None:
                            rfonts = etree.SubElement(rpr, qn("w", "rFonts"))
                        rfonts.set(qn("w", "ascii"), "Times New Roman")
                        rfonts.set(qn("w", "hAnsi"), "Times New Roman")
                        rfonts.set(qn("w", "cs"), "Times New Roman")

                        sz = rpr.find(qn("w", "sz"))
                        if sz is None:
                            sz = etree.SubElement(rpr, qn("w", "sz"))
                        sz.set(qn("w", "val"), "20")
                        sz_cs = rpr.find(qn("w", "szCs"))
                        if sz_cs is None:
                            sz_cs = etree.SubElement(rpr, qn("w", "szCs"))
                        sz_cs.set(qn("w", "val"), "20")

        print("Tabla 8 calibrada con exito (anchos 2800/6500 dxa, 10pt, interlineado sencillo y especificaciones completas).")
        cirujano._dirty = True

    # ─────────────────────────────────────────────────────────────────────────
    # 3. INYECTAR TABLA 9 EN SECCION 3.2 (Proveedores y disponibilidad)
    # ─────────────────────────────────────────────────────────────────────────
    body = cirujano.tree.find(qn("w", "body"))
    nodos_32 = cirujano.find_by_xpath("//w:p[contains(., '3.2 Proveedores y disponibilidad')]")
    p_encabezado_32 = None
    for p_cand in nodos_32:
        if p_cand.getparent() == body:
            p_encabezado_32 = p_cand

    if p_encabezado_32 is not None:
        tablas_t9_existentes = cirujano.find_by_xpath("//w:tbl[.//w:t[contains(., 'Matriz de Proveedores') or contains(., 'Cómputo Cloud y Alojamiento')]]")
        if not tablas_t9_existentes:
            parrafo_intro = crear_parrafo_cuerpo(
                "Para garantizar la estabilidad, continuidad operativa y seguridad de la plataforma EmpleaTEC, "
                "los insumos y componentes de software se adquieren bajo modelos de contratación como servicio "
                "(SaaS, PaaS e IaaS). La provisión de estos recursos tecnológicos se realiza a través de proveedores líderes "
                "en la industria del software e infraestructura cloud, asegurando una disponibilidad ininterrumpida, "
                "tiempos de aprovisionamiento inmediatos y un esquema elástico con alta tolerancia a fallos."
            )
            parrafo_conector = crear_parrafo_cuerpo(
                "En la siguiente matriz se detallan los proveedores seleccionados, las especificaciones de suministro, "
                "los niveles de servicio garantizados (SLA) y las condiciones comerciales de contratación:"
            )

            etiquetas_t9 = crear_etiqueta_tabla(
                9, "Matriz de Proveedores y Disponibilidad de Recursos e Insumos Tecnológicos"
            )

            encabezados_t9 = [
                "Insumo / Recurso Tecnológico",
                "Proveedor Seleccionado",
                "Disponibilidad y Nivel de Servicio (SLA)",
                "Condiciones de Adquisición y Contratación"
            ]
            filas_datos_t9 = [
                [
                    "Cómputo Cloud y Alojamiento Web",
                    "Amazon Web Services (AWS) / Vercel Inc.",
                    "Disponibilidad global continua 24/7/365 (SLA contractual de 99.95% de tiempo de actividad).",
                    "Suscripción mensual bajo demanda por consumo elástico de recursos y ancho de banda (Pay-as-you-go)."
                ],
                [
                    "Base de Datos y Autenticación",
                    "Supabase Inc. / AWS RDS PostgreSQL",
                    "Disponibilidad multi-zona con replicación activa inmediata y tolerancia a fallos regional.",
                    "Plan Pro institucional con facturación mensual cubierta por partida de tecnologías de la información."
                ],
                [
                    "Repositorios de Código y CI/CD",
                    "GitHub Inc. (Microsoft Corporation)",
                    "Infraestructura cloud distribuida con disponibilidad del 99.9% y respaldos redundantes.",
                    "Licenciamiento GitHub Education / Team subvencionado institucionalmente para el ITSNa."
                ],
                [
                    "Nombres de Dominio Institucionales",
                    "NIC México / Akky / Namecheap Inc.",
                    "Disponibilidad perpetua con renovación activa; propagación DNS global menor a 4 horas.",
                    "Adquisición anual del subdominio oficial (.edu.mx) vía TecNM y reserva de dominio comercial (.mx)."
                ],
                [
                    "Seguridad Perimetral, CDN y SSL",
                    "Cloudflare Inc. / Let's Encrypt",
                    "Red Anycast global en más de 300 ciudades; disponibilidad continua garantizada del 100%.",
                    "Capa WAF y certificado SSL con renovación criptográfica automatizada cada 90 días sin costo."
                ],
                [
                    "Servicio Transaccional de Correo",
                    "Resend Technologies / SendGrid (Twilio)",
                    "API en tiempo real con 99.9% de tasa de entrega exitosa de correos transaccionales.",
                    "Plan Developer con cuota mensual gratuita de 3,000 correos y tarificación por consumo excedente."
                ],
                [
                    "Equipamiento de Cómputo de Desarrollo",
                    "Distribuidores Autorizados (Dell / HP México)",
                    "Disponibilidad inmediata en almacén y entrega local en un periodo menor a 72 horas hábiles.",
                    "Compra con póliza de garantía de 3 años en sitio, financiada mediante fondos de residencia profesional."
                ],
                [
                    "Conectividad a Internet de Alta Velocidad",
                    "Telmex (Infinitum Empresarial) / Totalplay",
                    "Fibra óptica simétrica dedicada con disponibilidad del 99.5% y soporte técnico 24/7.",
                    "Contrato corporativo mensual con cargo centralizado a la administración del ITSNa."
                ]
            ]
            anchos_t9 = [2200, 2200, 2500, 2400]  # Total: 9300 dxa (6.45 pulgadas)

            tabla_ooxml_t9 = construir_tabla_ooxml(encabezados_t9, filas_datos_t9, anchos_t9)
            nota_t9 = crear_nota_tabla("Elaboración propia con base en el catálogo de proveedores y requerimientos técnicos del proyecto EmpleaTEC.")

            idx_32 = body.index(p_encabezado_32)
            puntero_parrafos = idx_32 + 1
            while puntero_parrafos < len(body):
                elem = body[puntero_parrafos]
                if elem.tag == qn("w", "p"):
                    texto_elem = "".join((t.text or "") for t in elem.iter(qn("w", "t"))).strip()
                    if "3.3 Descripción del equipo" in texto_elem:
                        break
                    body.remove(elem)
                    continue
                puntero_parrafos += 1

            elementos_a_insertar = [
                parrafo_intro,
                parrafo_conector,
                etiquetas_t9[0],
                etiquetas_t9[1],
                tabla_ooxml_t9,
                nota_t9
            ]

            puntero_insercion = p_encabezado_32
            for el in elementos_a_insertar:
                puntero_insercion.addnext(el)
                puntero_insercion = el

            print("Tabla 9 y texto contextual inyectados en Seccion 3.2 con exito.")
            cirujano._dirty = True

    # ─────────────────────────────────────────────────────────────────────────
    # 4. HOMOGENEIZACIÓN DE INTERLINEADO Y ESTILOS
    # ─────────────────────────────────────────────────────────────────────────
    total_parrafos = 0
    parrafos_cuerpo = 0
    parrafos_celda = 0

    if body is not None:
        for p in body.iter(qn("w", "p")):
            total_parrafos += 1
            dentro_de_tabla = bool(p.xpath("ancestor::w:tbl", namespaces=NS))
            texto = "".join(p.itertext()).strip()

            ppr = p.find(qn("w", "pPr"))
            if ppr is None:
                ppr = etree.Element(qn("w", "pPr"))
                p.insert(0, ppr)

            if dentro_de_tabla:
                # Interlineado sencillo (240), sin sangria de primera linea
                esp = ppr.find(qn("w", "spacing"))
                if esp is None:
                    esp = etree.SubElement(ppr, qn("w", "spacing"))
                esp.set(qn("w", "line"), "240")
                esp.set(qn("w", "lineRule"), "auto")
                esp.set(qn("w", "before"), "60")
                esp.set(qn("w", "after"), "60")

                ind = ppr.find(qn("w", "ind"))
                if ind is None:
                    ind = etree.SubElement(ppr, qn("w", "ind"))
                ind.set(qn("w", "firstLine"), "0")
                parrafos_celda += 1
            else:
                es_etiqueta_o_nota = (
                    texto.startswith("Tabla ") or
                    texto.startswith("Figura ") or
                    texto.startswith("Nota.") or
                    texto.startswith("Capítulo ") or
                    texto.startswith("1.") or
                    texto.startswith("2.") or
                    texto.startswith("3.") or
                    texto.startswith("4.") or
                    texto.startswith("5.")
                )

                if es_etiqueta_o_nota:
                    esp = ppr.find(qn("w", "spacing"))
                    if esp is None:
                        esp = etree.SubElement(ppr, qn("w", "spacing"))
                    esp.set(qn("w", "line"), "240")
                    esp.set(qn("w", "lineRule"), "auto")
                    ind = ppr.find(qn("w", "ind"))
                    if ind is None:
                        ind = etree.SubElement(ppr, qn("w", "ind"))
                    ind.set(qn("w", "firstLine"), "0")
                elif len(texto) > 40:
                    esp = ppr.find(qn("w", "spacing"))
                    if esp is None:
                        esp = etree.SubElement(ppr, qn("w", "spacing"))
                    esp.set(qn("w", "line"), "480")
                    esp.set(qn("w", "lineRule"), "auto")
                    esp.set(qn("w", "before"), "0")
                    esp.set(qn("w", "after"), "0")

                    ind = ppr.find(qn("w", "ind"))
                    if ind is None:
                        ind = etree.SubElement(ppr, qn("w", "ind"))
                    ind.set(qn("w", "firstLine"), "720")
                    parrafos_cuerpo += 1

    print(f"Homogeneizacion completada: {total_parrafos} parrafos escaneados ({parrafos_cuerpo} cuerpo, {parrafos_celda} celdas).")

    # Guardar cambios
    resultado_commit = cirujano.commit_changes()
    print(f"Commit final exitoso: {resultado_commit}")

if __name__ == "__main__":
    archivo_objetivo = Path(r"C:\Users\carde\Desktop\tareas_504B\Indice para Desarrolo emprendedores A y B_LTHDA_CASI_DEFINITIVO.docx")
    procesar_documento(archivo_objetivo)

    archivo_v02 = Path(r"C:\Users\carde\Desktop\tareas_504B\2. Desarrollo de emprendedores\Indice para Desarrolo emprendedores A y B_LTHDA_V02.docx")
    if archivo_v02.exists():
        procesar_documento(archivo_v02)
