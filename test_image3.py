from src.surgeon import DocxSurgeon

def main():
    docx_path = r"C:\Users\carde\Desktop\MUACK\Unidad3_AccesoDatos_JoseAvilesCardenas_2.docx"
    out_path = r"C:\Users\carde\Desktop\MUACK\Unidad3_NONA_DOMINATION.docx"
    logo_nona = r"C:\Users\carde\.gemini\antigravity\brain\09c9cc28-d488-4ad6-9eb5-4fb3ab535591\nona_lava_neon_logo_1778306466848.png"
    
    surgeon = DocxSurgeon(docx_path)
    
    print("⚡ Reemplazando image1.jpeg (Logo ITSNa en portada)...")
    surgeon.surgical_replace_image(r_id=None, new_image_path=logo_nona, zip_target="word/media/image1.jpeg")
    
    print("⚡ Reemplazando image2.jpeg (Logo TIC's en portada)...")
    surgeon.surgical_replace_image(r_id=None, new_image_path=logo_nona, zip_target="word/media/image2.jpeg")
    
    print("⚡ Reemplazando image3.jpeg (Logo oculto en Header)...")
    surgeon.surgical_replace_image(r_id=None, new_image_path=logo_nona, zip_target="word/media/image3.jpeg")
    
    print("💾 Guardando...")
    surgeon.commit_changes(out_path)
    print("✅ ¡Dominación completada!")

if __name__ == "__main__":
    main()
