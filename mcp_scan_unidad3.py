import asyncio
import json
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

async def main():
    server_params = StdioServerParameters(
        command="C:\\Users\\carde\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe",
        args=["-m", "src.server"],
        cwd="C:\\Users\\carde\\Desktop\\MUACK\\LUCERO"
    )

    docx_path = r"C:\Users\carde\Desktop\MUACK\Unidad3_AccesoDatos_JoseAvilesCardenas_2.docx"
    print(f"🚀 [Gema] Conectando al servidor MCP para escanear:\n{docx_path}\n")
    
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            
            # Ejecutamos la herramienta de escaneo
            print("🔍 [Gema] Ejecutando 'inspect_xml_tree' vía MCP...\n")
            result = await session.call_tool("inspect_xml_tree", {
                "docx_path": docx_path,
                "max_paragraphs": 10  # Vamos a traer los primeros 10 párrafos para ver la estructura base
            })
            
            # Formateamos y mostramos la respuesta
            respuesta = json.loads(result.content[0].text)
            
            for p in respuesta:
                print(f"📝 Párrafo ID: {p.get('para_id', 'N/A')} (Índice: {p['para_index']})")
                print(f"   Estilo : {p.get('style', 'Normal')}")
                print(f"   Texto  : {p['text'][:80]}..." if len(p['text']) > 80 else f"   Texto  : {p['text']}")
                print(f"   XPath  : {p['xpath']}")
                print("   " + "-"*50)

if __name__ == "__main__":
    asyncio.run(main())
