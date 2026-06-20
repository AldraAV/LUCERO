from src.surgeon import DocxSurgeon
import json

def main():
    docx_path = r"C:\Users\carde\Desktop\MUACK\Unidad3_AccesoDatos_JoseAvilesCardenas_2.docx"
    out_path = r"C:\Users\carde\Desktop\MUACK\Unidad3_MODIFICADO_HEADER.docx"
    new_image_path = r"C:\Users\carde\.gemini\antigravity\brain\09c9cc28-d488-4ad6-9eb5-4fb3ab535591\nona_lava_neon_logo_1778306466848.png"
    
    print(f"🍒 Iniciando el Décimo Hermano (Cirugía de Imágenes en Headers)...")
    surgeon = DocxSurgeon(docx_path)
    
    # Reemplazar el logo del ITSNa que descubrimos que es image3.jpeg en el header2.xml
    zip_target = "word/media/image3.jpeg"
    print(f"⚡ Reemplazando imagen física {zip_target}...")
    
    result = surgeon.surgical_replace_image(r_id=None, new_image_path=new_image_path, zip_target=zip_target)
    
    if result.get("success"):
        print("✅ Logo del ITSNa destruido y reemplazado en memoria.")
        commit_result = surgeon.commit_changes(out_path)
        print(f"💾 Archivo guardado con éxito en:\n   {commit_result.get('output_path')}")
    else:
        print("❌ Error:", result)

if __name__ == "__main__":
    main()
