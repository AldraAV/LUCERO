"""
surgeon.py — Motor quirúrgico de manipulación XML.
Opera directamente sobre el document.xml del contenedor DOCX
usando lxml + XPath para precisión de nodo. Zero format loss.
"""

from __future__ import annotations

import copy
import io
import shutil
import zipfile
from pathlib import Path
from typing import Any

from lxml import etree

from .utils import NS, JsonDict, get_logger, qn, validate_docx

log = get_logger("aldradoc.surgeon")

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────────────────────
WORD_DOCUMENT  = "word/document.xml"
WORD_RELS      = "word/_rels/document.xml.rels"
CONTENT_TYPES  = "[Content_Types].xml"
REQUIRED_PARTS = {WORD_DOCUMENT, CONTENT_TYPES}


# ─────────────────────────────────────────────────────────────────────────────
# CLASE PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

class DocxSurgeon:
    """
    Abre un .docx en memoria, expone el árbol XML como lxml.Element
    y permite cirugías XPath sin reescribir partes intactas del ZIP.
    """

    def __init__(self, docx_path: str | Path) -> None:
        self.path = Path(docx_path)
        validate_docx(self.path)
        self._zip_bytes: bytes = self.path.read_bytes()
        self._tree: etree._Element | None = None
        self._rels_tree: etree._Element | None = None
        self._dirty: bool = False
        self.pending_writes: dict[str, bytes] = {}
        log.info("DocxSurgeon inicializado para: %s", self.path.name)

    # ── Propiedad lazy: árbol del document.xml ────────────────────────────────
    @property
    def tree(self) -> etree._Element:
        if self._tree is None:
            self._tree = self._load_xml(WORD_DOCUMENT)
            log.debug("document.xml parseado (%d nodos raíz)", len(self._tree))
        return self._tree

    @property
    def rels_tree(self) -> etree._Element:
        if self._rels_tree is None:
            self._rels_tree = self._load_xml(WORD_RELS)
        return self._rels_tree

    def _load_xml(self, member: str) -> etree._Element:
        with zipfile.ZipFile(io.BytesIO(self._zip_bytes)) as z:
            raw = z.read(member)
        parser = etree.XMLParser(remove_blank_text=False, recover=True)
        return etree.fromstring(raw, parser)

    def _serialize_xml(self, element: etree._Element) -> bytes:
        return etree.tostring(
            element,
            xml_declaration=True,
            encoding="UTF-8",
            standalone=True,
        )

    # ── Inspección del árbol ──────────────────────────────────────────────────

    def inspect_tree(self, max_paragraphs: int = 100) -> list[JsonDict]:
        """
        Devuelve el mapa estructural de párrafos y runs del document.xml.
        Incluye: índice, paraId, estilo, texto completo y runs individuales.
        """
        log.info("Inspeccionando árbol XML (max %d párrafos)…", max_paragraphs)
        body = self.tree.find(qn("w", "body"))
        if body is None:
            raise RuntimeError("document.xml no contiene <w:body>")

        paragraphs = body.findall(f".//{qn('w', 'p')}")[:max_paragraphs]
        result: list[JsonDict] = []

        for idx, para in enumerate(paragraphs):
            # estilo
            ppr = para.find(qn("w", "pPr"))
            style_id = None
            if ppr is not None:
                ps = ppr.find(qn("w", "pStyle"))
                if ps is not None:
                    style_id = ps.get(qn("w", "val"))

            # paraId (w14)
            para_id = para.get(f"{{{NS['w14']}}}paraId") or para.get(f"{{{NS['w']}}}rsidR")

            # runs
            runs_data: list[JsonDict] = []
            for r_idx, run in enumerate(para.findall(qn("w", "r"))):
                rpr = run.find(qn("w", "rPr"))
                if rpr is not None:
                    b_el = rpr.find(qn("w", "b"))
                    bold_val = (b_el is not None and b_el.get(qn("w", "val"), "true").lower() not in ("0", "false"))
                    i_el = rpr.find(qn("w", "i"))
                    italic_val = (i_el is not None and i_el.get(qn("w", "val"), "true").lower() not in ("0", "false"))
                    u_el = rpr.find(qn("w", "u"))
                    underline_val = (u_el is not None and u_el.get(qn("w", "val"), "none").lower() not in ("0", "none", "false"))
                    strike_el = rpr.find(qn("w", "strike"))
                    strike_val = (strike_el is not None and strike_el.get(qn("w", "val"), "true").lower() not in ("0", "false"))
                else:
                    bold_val = False
                    italic_val = False
                    underline_val = False
                    strike_val = False

                fmt: dict[str, bool] = {
                    "bold":      bold_val,
                    "italic":    italic_val,
                    "underline": underline_val,
                    "strike":    strike_val,
                }
                t_el = run.find(qn("w", "t"))
                text = (t_el.text or "") if t_el is not None else ""
                runs_data.append({
                    "run_index": r_idx,
                    "text": text,
                    "format": fmt,
                    "xpath": f"(//w:body//w:p)[{idx + 1}]/w:r[{r_idx + 1}]",
                })

            full_text = "".join(rd["text"] for rd in runs_data)
            log.debug("  p[%d] style=%s text=%r", idx, style_id, full_text[:60])

            result.append({
                "para_index": idx,
                "para_id":    para_id,
                "style":      style_id,
                "text":       full_text,
                "runs":       runs_data,
                "xpath":      f"(//w:body//w:p)[{idx + 1}]",
            })

        log.info("Inspeccion completada: %d parrafos encontrados", len(result))
        return result

    def inspect_images(self) -> list[dict[str, Any]]:
        """Extrae todas las imágenes (a:blip o v:imagedata) del documento."""
        log.info("Inspeccionando imágenes en el documento...")
        result = []
        
        # Buscar a:blip
        for blip in self.tree.findall(".//{http://schemas.openxmlformats.org/drawingml/2006/main}blip"):
            embed = blip.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
            if embed:
                result.append({"rId": embed, "type": "blip"})
                
        # Buscar v:imagedata (formatos viejos / VML)
        for imagedata in self.tree.findall(".//{urn:schemas-microsoft-com:vml}imagedata"):
            embed = imagedata.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            if embed:
                result.append({"rId": embed, "type": "vml"})
                
        # Cruzar con rels para obtener el Target físico
        for item in result:
            rel_node = self.rels_tree.find(f".//{{http://schemas.openxmlformats.org/package/2006/relationships}}Relationship[@Id='{item['rId']}']")
            if rel_node is not None:
                item["target"] = rel_node.get("Target")
                
        # Deduplicar
        unique_results = list({f"{r['rId']}": r for r in result}.values())
        log.info("Imágenes encontradas: %s", unique_results)
        return unique_results

    def texto_parrafo(self, p_node: etree._Element) -> str:
        """Devuelve el texto completo concatenado de todos los runs de un párrafo."""
        return "".join((t.text or "") for t in p_node.iter(qn("w", "t")))

    # ── Reemplazo quirúrgico de texto ─────────────────────────────────────────

    def surgical_replace(
        self,
        target_text: str,
        replacement_text: str,
        occurrence: int = 1,
    ) -> dict[str, Any]:
        """
        Localiza 'target_text' dentro de runs <w:t> y lo reemplaza
        preservando 100% del formato del <w:r> que lo contiene.

        Maneja runs simples Y runs fragmentados (texto dividido entre
        varios <w:r> consecutivos por autocorrección de Word).

        occurrence: qué aparición reemplazar (1 = primera, 2 = segunda, -1 = todas).
        """
        log.info("surgical_replace: %r → %r (occurrence=%d)",
                 target_text, replacement_text, occurrence)

        body = self.tree.find(qn("w", "body"))
        if body is None:
            raise RuntimeError("No se encontró <w:body>")

        # 1. Encontrar todas las apariciones a lo largo del documento
        coincidencias: list[dict[str, Any]] = []

        for p_idx, para in enumerate(body.iter(qn("w", "p"))):
            runs = para.findall(f".//{qn('w', 'r')}")
            if not runs:
                continue

            para_text = "".join(
                (r.find(qn("w", "t")).text or "")
                for r in runs
                if r.find(qn("w", "t")) is not None
            )

            if target_text not in para_text:
                continue

            # Mapear rangos de caracteres de cada run
            mapa_runs: list[tuple[etree._Element, etree._Element, str, int, int]] = []
            cursor = 0
            for run in runs:
                t_el = run.find(qn("w", "t"))
                if t_el is not None:
                    txt = t_el.text or ""
                    mapa_runs.append((run, t_el, txt, cursor, cursor + len(txt)))
                    cursor += len(txt)

            # Buscar todas las posiciones de target_text en el texto del párrafo
            pos = 0
            while True:
                idx_hallado = para_text.find(target_text, pos)
                if idx_hallado == -1:
                    break
                idx_fin = idx_hallado + len(target_text)

                # Verificar si cae dentro de un único run
                en_run_unico = False
                for r, t_el, txt, r_ini, r_fin in mapa_runs:
                    if r_ini <= idx_hallado and idx_fin <= r_fin:
                        coincidencias.append({
                            "tipo": "single",
                            "para": para,
                            "run": r,
                            "t_el": t_el,
                            "run_ini": r_ini,
                            "run_fin": r_fin,
                            "local_ini": idx_hallado - r_ini,
                            "local_fin": idx_fin - r_ini,
                        })
                        en_run_unico = True
                        break

                if not en_run_unico:
                    coincidencias.append({
                        "tipo": "multi",
                        "para": para,
                        "runs": runs,
                    })

                pos = idx_hallado + len(target_text)

        count_found = len(coincidencias)
        count_replaced = 0

        # 2. Determinar cuáles coincidencias reemplazar
        indices_a_reemplazar: list[int] = []
        if occurrence == -1:
            indices_a_reemplazar = list(range(count_found))
        elif 1 <= occurrence <= count_found:
            indices_a_reemplazar = [occurrence - 1]

        # 3. Aplicar reemplazos de mayor a menor para evitar corrimientos
        for idx in sorted(indices_a_reemplazar, reverse=True):
            m = coincidencias[idx]
            if m["tipo"] == "single":
                t_el = m["t_el"]
                txt_actual = t_el.text or ""
                nuevo_txt = txt_actual[:m["local_ini"]] + replacement_text + txt_actual[m["local_fin"]:]
                t_el.text = nuevo_txt
                if nuevo_txt.strip() != nuevo_txt:
                    t_el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                count_replaced += 1
                self._dirty = True
            elif m["tipo"] == "multi":
                reemplazado = self._replace_fragmented(m["runs"], target_text, replacement_text)
                if reemplazado:
                    count_replaced += 1
                    self._dirty = True

        result = {
            "target": target_text,
            "replacement": replacement_text,
            "occurrences_found": count_found,
            "occurrences_replaced": count_replaced,
            "dirty": self._dirty,
        }
        log.info("surgical_replace completado: %s", result)
        return result

    def _replace_fragmented(
        self,
        runs: list[etree._Element],
        target: str,
        replacement: str,
    ) -> bool:
        """
        Intenta reemplazar texto que está fragmentado en múltiples <w:r> consecutivos.
        Junta el texto de todos los runs, localiza el target, y reconstruye
        el primer run con el texto completo, vaciando los demás.
        """
        texts = []
        t_elements: list[tuple[etree._Element, etree._Element]] = []

        for run in runs:
            t_el = run.find(qn("w", "t"))
            if t_el is not None:
                texts.append(t_el.text or "")
                t_elements.append((run, t_el))

        joined = "".join(texts)
        if target not in joined:
            return False

        new_joined = joined.replace(target, replacement, 1)

        # Poner todo el texto en el primer run y vaciar el resto
        if t_elements:
            first_run, first_t = t_elements[0]
            first_t.text = new_joined
            if new_joined.strip() != new_joined:
                first_t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            for _, t_el in t_elements[1:]:
                t_el.text = ""
            log.info("  [MULTI-RUN] fragmentado resuelto, %d runs fusionados",
                     len(t_elements))
            return True
        return False

    # ── Inserción y Clonación Estructural ─────────────────────────────────────

    def insertar_parrafo_clonado(
        self,
        texto_ancla: str,
        segmentos: list[str],
        posicion: str = "despues",
    ) -> dict[str, Any]:
        """
        Inserta un nuevo párrafo clonando el pPr del párrafo ancla y
        creando runs que heredan el formato de los runs originales.
        """
        body = self.tree.find(qn("w", "body"))
        if body is None:
            return {"success": False, "error": "No se encontró <w:body>"}

        anchor_para = None
        for p in body.findall(f".//{qn('w', 'p')}"):
            p_text = "".join((t.text or "") for t in p.iter(qn("w", "t")))
            if texto_ancla in p_text:
                anchor_para = p
                break

        if anchor_para is None:
            return {"success": False, "error": f"Ancla {texto_ancla!r} no encontrada"}

        nuevo_p = etree.Element(qn("w", "p"))
        anchor_ppr = anchor_para.find(qn("w", "pPr"))
        if anchor_ppr is not None:
            nuevo_p.append(copy.deepcopy(anchor_ppr))

        anchor_runs = anchor_para.findall(qn("w", "r"))
        for idx, seg in enumerate(segmentos):
            nuevo_r = etree.SubElement(nuevo_p, qn("w", "r"))
            if idx < len(anchor_runs):
                orig_rpr = anchor_runs[idx].find(qn("w", "rPr"))
                if orig_rpr is not None:
                    nuevo_r.append(copy.deepcopy(orig_rpr))
            elif anchor_runs:
                orig_rpr = anchor_runs[-1].find(qn("w", "rPr"))
                if orig_rpr is not None:
                    nuevo_r.append(copy.deepcopy(orig_rpr))

            t_el = etree.SubElement(nuevo_r, qn("w", "t"))
            t_el.text = seg
            if seg.strip() != seg:
                t_el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")

        if posicion.lower() in ("despues", "después", "after"):
            anchor_para.addnext(nuevo_p)
        else:
            anchor_para.addprevious(nuevo_p)

        self._dirty = True
        return {"success": True, "paragraph": nuevo_p}

    # ── Lotes Atómicos de Operaciones ─────────────────────────────────────────

    def aplicar_lote(self, operaciones: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Aplica un lote de operaciones atómicas sobre el documento.
        Si alguna operación falla, se revierten todos los cambios en memoria.
        """
        arbol_respaldo = copy.deepcopy(self._tree) if self._tree is not None else None
        rels_respaldo = copy.deepcopy(self._rels_tree) if self._rels_tree is not None else None
        dirty_respaldo = self._dirty
        escrituras_respaldo = dict(self.pending_writes)

        for idx, op in enumerate(operaciones):
            tipo = op.get("tipo")
            if tipo == "reemplazar":
                objetivo = op.get("objetivo", "")
                reemplazo = op.get("reemplazo", "")
                ocurrencia = op.get("ocurrencia", op.get("occurrence", 1))
                res = self.surgical_replace(
                    target_text=objetivo,
                    replacement_text=reemplazo,
                    occurrence=ocurrencia,
                )
                if res.get("occurrences_replaced", 0) == 0:
                    self._tree = arbol_respaldo
                    self._rels_tree = rels_respaldo
                    self._dirty = dirty_respaldo
                    self.pending_writes = escrituras_respaldo
                    return {
                        "exito": False,
                        "fallo_en": idx + 1,
                        "error": f"No se encontró el texto objetivo en la operación {idx + 1}: {objetivo!r}",
                    }
            elif tipo == "insertar_parrafo":
                ancla = op.get("texto_ancla", "")
                segmentos = op.get("segmentos", [])
                posicion = op.get("posicion", "despues")
                res = self.insertar_parrafo_clonado(
                    texto_ancla=ancla,
                    segmentos=segmentos,
                    posicion=posicion,
                )
                if not res.get("success"):
                    self._tree = arbol_respaldo
                    self._rels_tree = rels_respaldo
                    self._dirty = dirty_respaldo
                    self.pending_writes = escrituras_respaldo
                    return {
                        "exito": False,
                        "fallo_en": idx + 1,
                        "error": res.get("error", "Error al insertar párrafo"),
                    }
            else:
                self._tree = arbol_respaldo
                self._rels_tree = rels_respaldo
                self._dirty = dirty_respaldo
                self.pending_writes = escrituras_respaldo
                return {
                    "exito": False,
                    "fallo_en": idx + 1,
                    "error": f"Tipo de operación desconocido: {tipo!r}",
                }

        return {"exito": True, "operaciones_aplicadas": len(operaciones)}

    # ── Ensamblado de Plantilla Maestra ───────────────────────────────────────

    def ensamblar_plantilla_maestra(
        self,
        ruta_hoja_presentacion: str | Path | None = None,
        ruta_contenido_cuerpo: str | Path | None = None,
        ancla_indice: str = "Índice",
        ancla_cuerpo_destino: str = "Resumen viejo",
        ancla_cuerpo_origen: str = "Resumen",
        identificador_cuerpo_origen: str = "EmpleaTEC",
    ) -> dict[str, Any]:
        """
        Ensambla una plantilla maestra:
        - Integra hoja de presentación (si se proporciona) antes del índice.
        - Preserva el índice y la estructura previa.
        - Inyecta el contenido del cuerpo a partir del ancla destino.
        """
        body = self.tree.find(qn("w", "body"))
        if body is None:
            return {"success": False, "error": "No se encontró <w:body>"}

        elementos_cuerpo_inyectados = 0
        elementos_hoja_inyectados = 0

        # 1. Reemplazar o insertar hoja de presentación si se especifica
        if ruta_hoja_presentacion and Path(ruta_hoja_presentacion).exists():
            cirujano_hoja = DocxSurgeon(ruta_hoja_presentacion)
            hoja_body = cirujano_hoja.tree.find(qn("w", "body"))
            if hoja_body is not None:
                parrafos_hoja = [
                    copy.deepcopy(el) for el in hoja_body
                    if el.tag == qn("w", "p") and el.tag != qn("w", "sectPr")
                ]
                # Buscar ancla del índice en la plantilla
                idx_indice = -1
                for i, child in enumerate(body):
                    if child.tag == qn("w", "p"):
                        txt = "".join((t.text or "") for t in child.iter(qn("w", "t")))
                        if ancla_indice in txt:
                            idx_indice = i
                            break
                if idx_indice != -1 and parrafos_hoja:
                    # Remover párrafos antes del índice (portada vieja)
                    for k in range(idx_indice - 1, -1, -1):
                        if body[k].tag == qn("w", "p"):
                            body.remove(body[k])
                    # Inyectar párrafos de hoja al inicio
                    for offset, el in enumerate(parrafos_hoja):
                        body.insert(offset, el)
                        elementos_hoja_inyectados += 1

        # 2. Inyectar contenido del cuerpo
        if ruta_contenido_cuerpo and Path(ruta_contenido_cuerpo).exists():
            cirujano_cuerpo = DocxSurgeon(ruta_contenido_cuerpo)
            cuerpo_body = cirujano_cuerpo.tree.find(qn("w", "body"))
            if cuerpo_body is not None:
                # Extraer elementos a partir de ancla_cuerpo_origen o identificador
                elementos_origen = []
                capturando = False
                for el in cuerpo_body:
                    if el.tag == qn("w", "sectPr"):
                        continue
                    txt = "".join((t.text or "") for t in el.iter(qn("w", "t")))
                    if not capturando and (ancla_cuerpo_origen in txt or identificador_cuerpo_origen in txt):
                        capturando = True
                    if capturando:
                        elementos_origen.append(copy.deepcopy(el))

                if not elementos_origen:
                    # Si no hubo coincidencia con ancla, tomar todos los párrafos y tablas
                    elementos_origen = [
                        copy.deepcopy(el) for el in cuerpo_body
                        if el.tag in (qn("w", "p"), qn("w", "tbl"))
                    ]

                # Localizar ancla destino en plantilla
                nodo_destino = None
                for child in body:
                    if child.tag == qn("w", "p"):
                        txt = "".join((t.text or "") for t in child.iter(qn("w", "t")))
                        if ancla_cuerpo_destino in txt:
                            nodo_destino = child
                            break

                if nodo_destino is not None:
                    puntero = nodo_destino
                    for el in elementos_origen:
                        puntero.addnext(el)
                        puntero = el
                        elementos_cuerpo_inyectados += 1
                    body.remove(nodo_destino)
                else:
                    sect = body.find(qn("w", "sectPr"))
                    for el in elementos_origen:
                        if sect is not None:
                            sect.addprevious(el)
                        else:
                            body.append(el)
                        elementos_cuerpo_inyectados += 1

        self._dirty = True
        return {
            "success": True,
            "cuerpo_elementos": elementos_cuerpo_inyectados,
            "hoja_elementos": elementos_hoja_inyectados,
        }

    # ── Exportar a Markdown ───────────────────────────────────────────────────

    def exportar_a_markdown(self, ruta_salida_md: str | Path) -> dict[str, Any]:
        """
        Exporta el contenido de document.xml a un archivo Markdown limpio (.md).
        Preserva encabezados, párrafos y tablas básicas.
        """
        body = self.tree.find(qn("w", "body"))
        if body is None:
            return {"success": False, "error": "No se encontró <w:body>"}

        lineas_md: list[str] = []

        for elemento in body:
            if elemento.tag == qn("w", "p"):
                # Verificar si es encabezado
                ppr = elemento.find(qn("w", "pPr"))
                nivel_encabezado = 0
                if ppr is not None:
                    pstyle = ppr.find(qn("w", "pStyle"))
                    if pstyle is not None:
                        val = pstyle.get(qn("w", "val"), "").lower()
                        if "heading 1" in val or "título 1" in val or "titulo 1" in val or "heading1" in val:
                            nivel_encabezado = 1
                        elif "heading 2" in val or "título 2" in val or "titulo 2" in val or "heading2" in val:
                            nivel_encabezado = 2
                        elif "heading 3" in val or "título 3" in val or "titulo 3" in val or "heading3" in val:
                            nivel_encabezado = 3

                partes_texto: list[str] = []
                for run in elemento.findall(qn("w", "r")):
                    rpr = run.find(qn("w", "rPr"))
                    t_el = run.find(qn("w", "t"))
                    if t_el is None or not t_el.text:
                        continue
                    txt = t_el.text
                    es_negrita = rpr is not None and rpr.find(qn("w", "b")) is not None
                    es_cursiva = rpr is not None and rpr.find(qn("w", "i")) is not None

                    if es_negrita and es_cursiva:
                        partes_texto.append(f"***{txt.strip()}***")
                    elif es_negrita:
                        partes_texto.append(f"**{txt.strip()}**")
                    elif es_cursiva:
                        partes_texto.append(f"*{txt.strip()}*")
                    else:
                        partes_texto.append(txt)

                parrafo_md = "".join(partes_texto).strip()
                if parrafo_md:
                    if nivel_encabezado > 0:
                        prefijo = "#" * nivel_encabezado
                        lineas_md.append(f"{prefijo} {parrafo_md}\n")
                    else:
                        lineas_md.append(f"{parrafo_md}\n")

            elif elemento.tag == qn("w", "tbl"):
                filas = elemento.findall(qn("w", "tr"))
                if not filas:
                    continue
                matriz_tabla: list[list[str]] = []
                for fila in filas:
                    celdas = fila.findall(qn("w", "tc"))
                    fila_texto = []
                    for celda in celdas:
                        textos_celda = [t.text or "" for t in celda.iter(qn("w", "t"))]
                        fila_texto.append(" ".join(textos_celda).strip())
                    matriz_tabla.append(fila_texto)

                if matriz_tabla:
                    num_cols = max(len(f) for f in matriz_tabla)
                    for f in matriz_tabla:
                        while len(f) < num_cols:
                            f.append("")
                    encabezados = matriz_tabla[0]
                    lineas_md.append("| " + " | ".join(encabezados) + " |")
                    lineas_md.append("| " + " | ".join(["---"] * num_cols) + " |")
                    for fila_datos in matriz_tabla[1:]:
                        lineas_md.append("| " + " | ".join(fila_datos) + " |")
                    lineas_md.append("")

        contenido_md = "\n".join(lineas_md)
        salida = Path(ruta_salida_md)
        salida.parent.mkdir(parents=True, exist_ok=True)
        salida.write_text(contenido_md, encoding="utf-8")

        return {
            "success": True,
            "output_path": str(salida),
            "bytes_written": len(contenido_md.encode("utf-8")),
        }

    # ── Inyección de estructura APA ───────────────────────────────────────────

    def inject_apa_structure(
        self,
        anchor_text: str,
        nodes: list[etree._Element],
        position: str = "after",
    ) -> dict[str, Any]:
        """
        Inyecta una lista de nodos XML (plantillas APA) antes o después del
        párrafo que contiene 'anchor_text'. Usa XPath para localización exacta.

        position: 'before' | 'after' | 'replace'
        """
        log.info("inject_apa_structure: anchor=%r, %d nodos, position=%s",
                 anchor_text, len(nodes), position)

        body = self.tree.find(qn("w", "body"))
        if body is None:
            raise RuntimeError("No se encontró <w:body>")

        anchor_para: etree._Element | None = None
        anchor_idx: int = -1

        for idx, child in enumerate(body):
            if child.tag != qn("w", "p"):
                continue
            para_text = "".join(
                (t.text or "")
                for t in child.iter(qn("w", "t"))
            )
            if anchor_text in para_text:
                anchor_para = child
                anchor_idx = idx
                log.debug("Anclaje encontrado en body[%d]: %r", idx, para_text[:80])
                break

        if anchor_para is None:
            msg = f"No se encontró ningún párrafo con el texto: {anchor_text!r}"
            log.error(msg)
            return {"success": False, "error": msg}

        # Inyectar nodos en el orden correcto
        if position == "after":
            for offset, node in enumerate(nodes):
                body.insert(anchor_idx + 1 + offset, copy.deepcopy(node))
        elif position == "before":
            for offset, node in enumerate(nodes):
                body.insert(anchor_idx + offset, copy.deepcopy(node))
        elif position == "replace":
            body.remove(anchor_para)
            for offset, node in enumerate(nodes):
                body.insert(anchor_idx + offset, copy.deepcopy(node))
        else:
            raise ValueError(f"position inválido: {position!r}. Usa 'before', 'after' o 'replace'")

        self._dirty = True
        result = {
            "success":    True,
            "anchor":     anchor_text,
            "position":   position,
            "nodes_injected": len(nodes),
            "anchor_body_index": anchor_idx,
        }
        log.info("Inyeccion completada: %s", result)
        return result

    # ── Inyección y Reemplazo de Imágenes ─────────────────────────────────────

    def surgical_replace_image(self, r_id: str | None, new_image_path: str | Path, zip_target: str | None = None) -> dict[str, Any]:
        """Sustituye físicamente una imagen en el ZIP. Puede buscar por r_id en document.xml.rels o usar zip_target directo."""
        log.info("surgical_replace_image: r_id=%r, zip_target=%r, path=%r", r_id, zip_target, new_image_path)
        
        if not zip_target:
            if not r_id:
                return {"success": False, "error": "Se debe proveer r_id o zip_target"}
            rel_node = self.rels_tree.find(f".//{{http://schemas.openxmlformats.org/package/2006/relationships}}Relationship[@Id='{r_id}']")
            if rel_node is None:
                return {"success": False, "error": f"No se encontró la relación {r_id} en document.xml.rels"}
            
            target = rel_node.get("Target")
            if not target:
                return {"success": False, "error": f"La relación {r_id} no tiene atributo Target"}
                
            zip_target = target[1:] if target.startswith("/") else f"word/{target}"
            
        img_path = Path(new_image_path)
        if not img_path.exists():
            return {"success": False, "error": f"La nueva imagen no existe: {img_path}"}
            
        img_bytes = img_path.read_bytes()
        self.pending_writes[zip_target] = img_bytes
        self._dirty = True
        
        result = {"success": True, "r_id": r_id, "replaced_file": zip_target, "bytes_written": len(img_bytes)}
        log.info("Reemplazo de imagen preparado: %s", result)
        return result

    def surgical_inject_image(self, xpath_expr: str, new_image_path: str | Path) -> dict[str, Any]:
        """Inyecta un nuevo nodo <w:drawing> y crea sus relaciones en el DOCX."""
        rels = self.rels_tree.findall(".//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship")
        max_id = 0
        for rel in rels:
            rid = rel.get("Id")
            if rid and rid.startswith("rId"):
                try:
                    num = int(rid[3:])
                    max_id = max(max_id, num)
                except ValueError: pass
        
        new_rid = f"rId{max_id + 1}"
        img_path = Path(new_image_path)
        if not img_path.exists():
            return {"success": False, "error": f"La imagen no existe: {img_path}"}
            
        img_bytes = img_path.read_bytes()
        ext = img_path.suffix.lower() or ".png"
        target_name = f"media/image_injected_{max_id + 1}{ext}"
        zip_target = f"word/{target_name}"
        
        new_rel = etree.SubElement(self.rels_tree, "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship")
        new_rel.set("Id", new_rid)
        new_rel.set("Type", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image")
        new_rel.set("Target", target_name)
        
        self.pending_writes[zip_target] = img_bytes
        
        nodes = self.find_by_xpath(xpath_expr)
        if not nodes:
            return {"success": False, "error": f"XPath no encontró ningún nodo: {xpath_expr}"}
            
        cx = 3 * 914400
        cy = 3 * 914400
        
        drawing_xml = f"""
        <w:drawing xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
            <wp:inline distT="0" distB="0" distL="0" distR="0">
                <wp:extent cx="{cx}" cy="{cy}"/>
                <wp:effectExtent l="0" t="0" r="0" b="0"/>
                <wp:docPr id="{max_id + 1}" name="InjectedImage{max_id + 1}"/>
                <wp:cNvGraphicFramePr>
                    <a:graphicFrameLocks noChangeAspect="1"/>
                </wp:cNvGraphicFramePr>
                <a:graphic>
                    <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
                        <pic:pic>
                            <pic:nvPicPr>
                                <pic:cNvPr id="{max_id + 1}" name="InjectedImage{ext}"/>
                                <pic:cNvPicPr/>
                            </pic:nvPicPr>
                            <pic:blipFill>
                                <a:blip r:embed="{new_rid}"/>
                                <a:stretch>
                                    <a:fillRect/>
                                </a:stretch>
                            </pic:blipFill>
                            <pic:spPr>
                                <a:xfrm>
                                    <a:off x="0" y="0"/>
                                    <a:ext cx="{cx}" cy="{cy}"/>
                                </a:xfrm>
                                <a:prstGeom prst="rect">
                                    <a:avLst/>
                                </a:prstGeom>
                            </pic:spPr>
                        </pic:pic>
                    </a:graphicData>
                </a:graphic>
            </wp:inline>
        </w:drawing>
        """
        drawing_el = etree.fromstring(drawing_xml.strip())
        
        for node in nodes:
            r_el = etree.SubElement(node, "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r")
            r_el.append(copy.deepcopy(drawing_el))
            
        self._dirty = True
        return {"success": True, "injected_rId": new_rid, "target": zip_target, "xpath": xpath_expr}

    # ── Mutación Quirúrgica de Estilos (Full Format Control) ──────────────────

    def surgical_style_edit(
        self,
        xpath_expr: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Inyecta o modifica propiedades OOXML en un nodo específico (w:p o w:r).
        """
        log.info("surgical_style_edit en %r con propiedades: %r", xpath_expr, properties)
        nodes = self.find_by_xpath(xpath_expr)
        if not nodes:
            return {"success": False, "error": f"XPath no encontró ningún nodo: {xpath_expr}"}

        modified_count = 0
        for node in nodes:
            if node.tag == qn("w", "p"):
                self._apply_pPr(node, properties)
                for run in node.findall(f".//{qn('w', 'r')}"):
                    self._apply_rPr(run, properties)
                modified_count += 1
            elif node.tag == qn("w", "r"):
                self._apply_rPr(node, properties)
                modified_count += 1
            elif node.tag == qn("w", "tbl"):
                self._apply_tblPr(node, properties)
                modified_count += 1
            else:
                log.warning("El nodo objetivo no es w:p, w:r ni w:tbl: %s", node.tag)

        self._dirty = modified_count > 0
        return {
            "success": True,
            "nodes_modified": modified_count,
            "xpath": xpath_expr,
            "dirty": self._dirty
        }

    def _apply_tblPr(self, tbl_node: etree._Element, props: dict[str, Any]) -> None:
        tblPr = tbl_node.find(qn("w", "tblPr"))
        if tblPr is None:
            tblPr = etree.Element(qn("w", "tblPr"))
            tbl_node.insert(0, tblPr)
            
        margin_props = ["margin_top", "margin_left", "margin_bottom", "margin_right"]
        if any(p in props for p in margin_props):
            tblCellMar = tblPr.find(qn("w", "tblCellMar"))
            if tblCellMar is None:
                tblCellMar = etree.SubElement(tblPr, qn("w", "tblCellMar"))
                
            if "margin_top" in props:
                top = tblCellMar.find(qn("w", "top"))
                if top is None:
                    top = etree.SubElement(tblCellMar, qn("w", "top"))
                top.set(qn("w", "w"), str(props["margin_top"]))
                top.set(qn("w", "type"), "dxa")
                
            if "margin_bottom" in props:
                bottom = tblCellMar.find(qn("w", "bottom"))
                if bottom is None:
                    bottom = etree.SubElement(tblCellMar, qn("w", "bottom"))
                bottom.set(qn("w", "w"), str(props["margin_bottom"]))
                bottom.set(qn("w", "type"), "dxa")
                
            if "margin_left" in props:
                left = tblCellMar.find(qn("w", "left"))
                if left is None:
                    left = etree.SubElement(tblCellMar, qn("w", "left"))
                left.set(qn("w", "w"), str(props["margin_left"]))
                left.set(qn("w", "type"), "dxa")
                
            if "margin_right" in props:
                right = tblCellMar.find(qn("w", "right"))
                if right is None:
                    right = etree.SubElement(tblCellMar, qn("w", "right"))
                right.set(qn("w", "w"), str(props["margin_right"]))
                right.set(qn("w", "type"), "dxa")

    def _apply_pPr(self, p_node: etree._Element, props: dict[str, Any]) -> None:
        pPr = p_node.find(qn("w", "pPr"))
        if pPr is None:
            pPr = etree.Element(qn("w", "pPr"))
            p_node.insert(0, pPr)

        if "align" in props:
            jc = pPr.find(qn("w", "jc"))
            if jc is None:
                jc = etree.SubElement(pPr, qn("w", "jc"))
            jc.set(qn("w", "val"), props["align"])

        if "indent_left" in props or "indent_hanging" in props:
            ind = pPr.find(qn("w", "ind"))
            if ind is None:
                ind = etree.SubElement(pPr, qn("w", "ind"))
            if "indent_left" in props:
                ind.set(qn("w", "left"), str(props["indent_left"]))
            if "indent_hanging" in props:
                ind.set(qn("w", "hanging"), str(props["indent_hanging"]))

        self._apply_rPr(pPr, props)

    def _apply_rPr(self, parent_node: etree._Element, props: dict[str, Any]) -> None:
        rPr = parent_node.find(qn("w", "rPr"))
        if rPr is None:
            if any(k in props for k in ["size", "font", "bold", "italic"]):
                rPr = etree.Element(qn("w", "rPr"))
                parent_node.insert(0, rPr)
            else:
                return

        if "size" in props:
            sz = rPr.find(qn("w", "sz"))
            if sz is None:
                sz = etree.SubElement(rPr, qn("w", "sz"))
            sz.set(qn("w", "val"), str(props["size"]))
            szCs = rPr.find(qn("w", "szCs"))
            if szCs is None:
                szCs = etree.SubElement(rPr, qn("w", "szCs"))
            szCs.set(qn("w", "val"), str(props["size"]))

        if "font" in props:
            rFonts = rPr.find(qn("w", "rFonts"))
            if rFonts is None:
                rFonts = etree.SubElement(rPr, qn("w", "rFonts"))
            rFonts.set(qn("w", "ascii"), props["font"])
            rFonts.set(qn("w", "hAnsi"), props["font"])
            rFonts.set(qn("w", "cs"), props["font"])

        if props.get("bold") is True:
            if rPr.find(qn("w", "b")) is None:
                etree.SubElement(rPr, qn("w", "b"))
        elif props.get("bold") is False:
            b_el = rPr.find(qn("w", "b"))
            if b_el is not None:
                rPr.remove(b_el)

        if props.get("italic") is True:
            if rPr.find(qn("w", "i")) is None:
                etree.SubElement(rPr, qn("w", "i"))
        elif props.get("italic") is False:
            i_el = rPr.find(qn("w", "i"))
            if i_el is not None:
                rPr.remove(i_el)

    # ── Commit: reempaquetado seguro del ZIP ──────────────────────────────────

    def commit_changes(self, output_path: str | Path | None = None) -> dict[str, Any]:
        """
        Reempaqueta el DOCX con el document.xml modificado.
        Preserva: [Content_Types].xml, relaciones, imágenes y todos
        los demás miembros del ZIP sin tocarlos.

        Si output_path es None o es igual al archivo original, genera
        una copia de respaldo (.bak) y sobreescribe el original.
        """
        if not self._dirty:
            log.warning("commit_changes llamado sin cambios pendientes. Abortando.")
            return {"committed": False, "reason": "no hay cambios pendientes"}

        out = Path(output_path) if output_path else self.path
        log.info("Committing cambios a: %s", out)

        backup_path = None
        if out.resolve() == self.path.resolve() and self.path.exists():
            backup_file = self.path.with_suffix(self.path.suffix + ".bak")
            shutil.copy2(self.path, backup_file)
            backup_path = str(backup_file)

        # Serializar el árbol modificado
        new_doc_xml = self._serialize_xml(self.tree)
        log.debug("document.xml serializado (%d bytes)", len(new_doc_xml))

        out_buffer = io.BytesIO()
        self.pending_writes[WORD_DOCUMENT] = new_doc_xml
        if self._rels_tree is not None:
            self.pending_writes[WORD_RELS] = self._serialize_xml(self.rels_tree)

        with zipfile.ZipFile(io.BytesIO(self._zip_bytes)) as src_zip:
            names = set(src_zip.namelist())
            missing = REQUIRED_PARTS - names
            if missing:
                raise RuntimeError(f"DOCX corrupto: faltan partes: {missing}")

            with zipfile.ZipFile(out_buffer, "w", zipfile.ZIP_DEFLATED) as dst_zip:
                for item in src_zip.infolist():
                    if item.filename in self.pending_writes:
                        dst_zip.writestr(item, self.pending_writes.pop(item.filename))
                        log.debug("  [REPLACED] %s", item.filename)
                    else:
                        dst_zip.writestr(item, src_zip.read(item.filename))
                        
                for filename, data in self.pending_writes.items():
                    dst_zip.writestr(filename, data)
                    log.debug("  [ADDED] %s", filename)

        out.write_bytes(out_buffer.getvalue())
        size_kb = out.stat().st_size / 1024
        self._dirty = False

        result = {
            "committed":   True,
            "output_path": str(out),
            "size_kb":     round(size_kb, 1),
            "xml_size_bytes": len(new_doc_xml),
            "backup_path": backup_path,
        }
        log.info("Commit exitoso: %s (%.1f KB)", out.name, size_kb)
        return result

    # ── Utilidades adicionales ────────────────────────────────────────────────

    def find_by_xpath(self, xpath_expr: str) -> list[etree._Element]:
        """Ejecuta una expresión XPath arbitraria sobre el document.xml."""
        log.debug("XPath: %s", xpath_expr)
        return self.tree.xpath(xpath_expr, namespaces=NS)

    def get_styles_list(self) -> list[str]:
        """Lista todos los estilos usados en el documento."""
        styles: list[str] = []
        for ps in self.tree.iter(qn("w", "pStyle")):
            val = ps.get(qn("w", "val"))
            if val and val not in styles:
                styles.append(val)
        for rs in self.tree.iter(qn("w", "rStyle")):
            val = rs.get(qn("w", "val"))
            if val and val not in styles:
                styles.append(val)
        log.debug("Estilos encontrados: %s", styles)
        return sorted(styles)

    def discard_changes(self) -> None:
        """Descarta todos los cambios en memoria y recarga desde disco."""
        self._tree = None
        self._rels_tree = None
        self._dirty = False
        log.info("Cambios descartados. Árbol recargado.")

    def replace_section_content(self, anchor_heading_text: str, new_xml_elements: list[etree._Element]) -> dict[str, Any]:
        """
        Encuentra el encabezado indicado y reemplaza todo su contenido (hasta el siguiente 
        encabezado del mismo nivel o superior) con los nuevos elementos XML.
        """
        body = self.tree.find(qn("w", "body"))
        if body is None:
            return {"success": False, "msg": "No se encontro el body."}
            
        children = list(body)
        start_idx = -1
        heading_level = 0
        
        for i, p in enumerate(children):
            if p.tag != qn("w", "p"): continue
            texto = "".join(p.itertext()).strip()
            if anchor_heading_text in texto:
                start_idx = i
                pPr = p.find(qn("w", "pPr"))
                if pPr is not None:
                    pStyle = pPr.find(qn("w", "pStyle"))
                    if pStyle is not None:
                        val = pStyle.get(qn("w", "val"))
                        if val and val.startswith("Ttulo"):
                            try:
                                heading_level = int(val.replace("Ttulo", ""))
                            except:
                                pass
                break
                
        if start_idx == -1:
            return {"success": False, "msg": f"Heading no encontrado: {anchor_heading_text}"}
            
        end_idx = len(children)
        if heading_level > 0:
            for i in range(start_idx + 1, len(children)):
                p = children[i]
                if p.tag != qn("w", "p"): continue
                pPr = p.find(qn("w", "pPr"))
                if pPr is not None:
                    pStyle = pPr.find(qn("w", "pStyle"))
                    if pStyle is not None:
                        val = pStyle.get(qn("w", "val"))
                        if val and val.startswith("Ttulo"):
                            try:
                                lvl = int(val.replace("Ttulo", ""))
                                if lvl <= heading_level:
                                    end_idx = i
                                    break
                            except:
                                pass
                                
        removed = 0
        for i in range(start_idx + 1, end_idx):
            body.remove(children[i])
            removed += 1
            
        puntero = children[start_idx]
        for el in new_xml_elements:
            puntero.addnext(el)
            puntero = el
            
        self._dirty = True
        return {"success": True, "removed": removed, "injected": len(new_xml_elements)}
