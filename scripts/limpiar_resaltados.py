"""
limpiar_resaltados.py — Script oficial de mantenimiento de LUCERO.
Utiliza DocxSurgeon para retirar todos los nodos <w:highlight>
garantizando cero perdida de formato y preservacion de ECMA-376.
"""
from pathlib import Path
import sys

# Agregar raiz de LUCERO al sys.path
lucero_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(lucero_root))

from src.surgeon import DocxSurgeon
from src.utils import qn

def limpiar_resaltados(doc_path: Path):
    print(f"Abriendo documento con DocxSurgeon: {doc_path.name}")
    surgeon = DocxSurgeon(doc_path)
    
    # Localizar todos los elementos w:highlight
    highlights = surgeon.find_by_xpath("//w:highlight")
    print(f"Resaltados encontrados: {len(highlights)}")
    
    eliminados = 0
    for hl in highlights:
        padre = hl.getparent()
        if padre is not None:
            padre.remove(hl)
            eliminados += 1
            
    surgeon._dirty = eliminados > 0
    print(f"Nodos w:highlight removidos: {eliminados}")
    
    res = surgeon.commit_changes()
    print(f"Commit completado: {res}")
    
    # Verificacion
    verif_surgeon = DocxSurgeon(doc_path)
    restantes = len(verif_surgeon.find_by_xpath("//w:highlight"))
    print(f"Verificacion final w:highlight restantes: {restantes}")

if __name__ == "__main__":
    target = Path(r"C:\Users\carde\Desktop\tareas_504B\2. Desarrollo de emprendedores\Indice para Desarrolo emprendedores A y B_LTHDA_V02.docx")
    limpiar_resaltados(target)
