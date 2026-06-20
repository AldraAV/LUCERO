from src.surgeon import DocxSurgeon
import sys

def main():
    docx_path = r"C:\Users\carde\Desktop\MUACK\Unidad3_AccesoDatos_JoseAvilesCardenas_2.docx"
    out_path = r"C:\Users\carde\Desktop\MUACK\Unidad3_MODIFICADO_v3.docx"
    
    print(f"🍒 Iniciando el Décimo Hermano...")
    print(f"📂 Archivo objetivo: {docx_path}")
    
    try:
        surgeon = DocxSurgeon(docx_path)
        
        # Vamos a atacar el párrafo 11, que corresponde al título de la práctica:
        # "Desarrollo de una aplicación web para una empresa con conexión a una base de datos MySQL"
        xpath_objetivo = "(//w:body//w:p)[11]"
        
        # Inyectamos el estilo (28pt = 56 medios puntos según OOXML)
        propiedades = {
            "bold": True,
            "size": 56,  # 28pt
            "align": "center",
            "font": "Arial Black"
        }
        
        print(f"⚡ Inyectando estilos quirúrgicos en {xpath_objetivo}...")
        print(f"Propiedades: {propiedades}")
        
        resultado_estilo = surgeon.surgical_style_edit(xpath_objetivo, propiedades)
        
        if resultado_estilo.get("success"):
            print("✅ Mutación OOXML completada en memoria.")
            resultado_commit = surgeon.commit_changes(out_path)
            print(f"💾 Archivo guardado con éxito en:\n   {resultado_commit['output_path']}")
        else:
            print("❌ Error en la mutación:", resultado_estilo)
            
    except Exception as e:
        print(f"🚨 Error del sistema: {e}")

if __name__ == "__main__":
    main()
