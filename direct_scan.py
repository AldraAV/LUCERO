from src.surgeon import DocxSurgeon
import sys

def main():
    docx_path = r"C:\Users\carde\Desktop\MUACK\Unidad3_AccesoDatos_JoseAvilesCardenas_2.docx"
    print(f"🚀 Escaneando: {docx_path}")
    try:
        surgeon = DocxSurgeon(docx_path)
        paragraphs = surgeon.inspect_tree(max_paragraphs=30)
        
        print(f"\n📊 Se encontraron {len(paragraphs)} párrafos. Mostrando los primeros 30:")
        for p in paragraphs:
            text = p['text'].replace('\n', ' ')
            if not text.strip():
                continue # Saltar vacíos para mejor legibilidad
                
            print(f"[{p['para_index']}] Estilo: {p.get('style', 'Normal')}")
            print(f"    Texto: {text[:100]}..." if len(text) > 100 else f"    Texto: {text}")
            print(f"    XPath: {p['xpath']}")
            print("-" * 60)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
