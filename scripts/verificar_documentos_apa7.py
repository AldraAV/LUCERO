"""
verificar_documentos_apa7.py — Script de verificacion de integridad APA 7 para DOCX.
"""
import sys
from pathlib import Path

raiz_lucero = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(raiz_lucero))

from src.surgeon import DocxSurgeon
from src.utils import NS, qn

def verificar_doc(ruta: Path):
    print(f"\n--- VERIFICANDO: {ruta.name} ---")
    cirujano = DocxSurgeon(ruta)

    # 1. Total de tablas
    tablas = cirujano.find_by_xpath("//w:tbl")
    print(f"Total de tablas encontradas: {len(tablas)}")

    # 2. Verificar Tabla 8
    t8_tbls = cirujano.find_by_xpath("//w:tbl[.//w:t[contains(., 'Servidor Web')]]")
    if t8_tbls:
        t8_grid = t8_tbls[0].find(qn("w", "tblGrid"))
        anchos_t8 = [c.get(qn("w", "w")) for c in t8_grid.findall(qn("w", "gridCol"))] if t8_grid is not None else []
        print(f"Tabla 8 anchos directos de columna (tblGrid/gridCol): {anchos_t8}")

    t8_sz = cirujano.find_by_xpath("//w:tbl[.//w:t[contains(., 'Servidor Web')]]//w:tc//w:sz")
    tamanos_t8 = set(s.get(qn("w", "val")) for s in t8_sz)
    print(f"Tabla 8 tamanos de fuente en celdas (medio punto): {tamanos_t8}")

    t8_line = cirujano.find_by_xpath("//w:tbl[.//w:t[contains(., 'Servidor Web')]]//w:tc//w:spacing")
    lineas_t8 = set(l.get(qn("w", "line")) for l in t8_line)
    print(f"Tabla 8 interlineados en celdas: {lineas_t8}")

    # 3. Verificar Tabla 9
    t9_cols = cirujano.find_by_xpath("//w:tbl[.//w:t[contains(., 'Cómputo Cloud y Alojamiento')]]//w:gridCol")
    anchos_t9 = [c.get(qn("w", "w")) for c in t9_cols]
    print(f"Tabla 9 anchos de columna (gridCol): {anchos_t9}")

    t9_sz = cirujano.find_by_xpath("//w:tbl[.//w:t[contains(., 'Cómputo Cloud y Alojamiento')]]//w:tc//w:sz")
    tamanos_t9 = set(s.get(qn("w", "val")) for s in t9_sz)
    print(f"Tabla 9 tamanos de fuente en celdas (medio punto): {tamanos_t9}")

    t9_line = cirujano.find_by_xpath("//w:tbl[.//w:t[contains(., 'Cómputo Cloud y Alojamiento')]]//w:tc//w:spacing")
    lineas_t9 = set(l.get(qn("w", "line")) for l in t9_line)
    print(f"Tabla 9 interlineados en celdas: {lineas_t9}")

    # 4. Verificar etiquetas de tablas presentes
    etiquetas = []
    for t_nodo in cirujano.find_by_xpath("//w:t[contains(., 'Tabla')]"):
        txt = (t_nodo.text or "").strip()
        if txt.startswith("Tabla "):
            etiquetas.append(txt)
    print(f"Etiquetas de tablas detectadas: {etiquetas}")

    # 4b. Buscar si hay lista o indice de tablas en las primeras paginas
    parrafos_indice = cirujano.find_by_xpath("//w:p[.//w:t[contains(., 'Índice de Tablas') or contains(., 'Indice de tablas') or contains(., 'Lista de Tablas') or contains(., 'Índice') or contains(., 'Indice')]]")
    print(f"Parrafos de posible indice encontrados: {len(parrafos_indice)}")
    for pi in parrafos_indice[:10]:
        print("  -> " + "".join(pi.itertext()).strip())

    # 5. Muestreo de interlineado en parrafos de cuerpo
    parrafos_cuerpo = cirujano.find_by_xpath("//w:body/w:p[not(ancestor::w:tbl) and string-length(normalize-space(.)) > 80]")
    espaciados_cuerpo = set()
    sangrias_cuerpo = set()
    for p in parrafos_cuerpo[:30]:
        esp = p.find(f".//{qn('w', 'spacing')}")
        if esp is not None:
            espaciados_cuerpo.add(esp.get(qn("w", "line")))
        ind = p.find(f".//{qn('w', 'ind')}")
        if ind is not None:
            sangrias_cuerpo.add(ind.get(qn("w", "firstLine")))
    print(f"Muestreo interlineado en parrafos de cuerpo (>80 chars): {espaciados_cuerpo}")
    print(f"Muestreo sangria primera linea en cuerpo: {sangrias_cuerpo}")

if __name__ == "__main__":
    verificar_doc(Path(r"C:\Users\carde\Desktop\tareas_504B\Indice para Desarrolo emprendedores A y B_LTHDA_CASI_DEFINITIVO.docx"))
    verificar_doc(Path(r"C:\Users\carde\Desktop\tareas_504B\2. Desarrollo de emprendedores\Indice para Desarrolo emprendedores A y B_LTHDA_V02.docx"))
