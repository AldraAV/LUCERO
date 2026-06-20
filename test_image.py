from src.surgeon import DocxSurgeon
import json

def main():
    docx_path = r"C:\Users\carde\Desktop\MUACK\Unidad3_AccesoDatos_JoseAvilesCardenas_2.docx"
    out_path = r"C:\Users\carde\Desktop\MUACK\Unidad3_MODIFICADO_IMG.docx"
    new_image_path = r"C:\Users\carde\.gemini\antigravity\brain\09c9cc28-d488-4ad6-9eb5-4fb3ab535591\nona_lava_neon_logo_1778306466848.png"
    
    print(f"🍒 Iniciando el Décimo Hermano (Cirugía de Imágenes)...")
    surgeon = DocxSurgeon(docx_path)
    
    # 1. Opción A: Reemplazar la primera imagen (rId9, que suele ser el logo en la portada)
    r_id_objetivo = "rId9"
    print(f"⚡ Inyectando nueva imagen en {r_id_objetivo}...")
    
    result = surgeon.surgical_replace_image(r_id_objetivo, new_image_path)
    if result.get("success"):
        print("✅ Imagen reemplazada en memoria.")
        commit_result = surgeon.commit_changes(out_path)
    # 2. Opción B: Inyectar una nueva imagen al final del párrafo 11
    xpath_inyeccion = "(//w:body//w:p)[11]"
    print(f"\n⚡ Inyectando imagen (Opción B) en {xpath_inyeccion}...")
    
    result_b = surgeon.surgical_inject_image(xpath_inyeccion, new_image_path)
    if result_b.get("success"):
        print(f"✅ Imagen inyectada en memoria (Nuevo rId: {result_b.get('injected_rId')}).")
        commit_result = surgeon.commit_changes(out_path)
        print(f"💾 Archivo guardado con éxito en:\n   {commit_result.get('output_path')}")
    else:
        print("❌ Error:", result_b)

if __name__ == "__main__":
    main()
