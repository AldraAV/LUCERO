import asyncio
import json
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

async def main():
    # 1. Configuramos cómo invocar al servidor (tal cual lo haría tu framework de IA)
    server_params = StdioServerParameters(
        command="C:\\Users\\carde\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe",
        args=["-m", "src.server"],
        cwd="C:\\Users\\carde\\Desktop\\MUACK\\LUCERO"
    )

    print("🚀 [LLM Client] Iniciando conexión stdio con LUCERO...")
    
    # 2. Establecemos la conexión de entrada/salida estándar
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # Inicializamos la sesión MCP
            await session.initialize()
            print("✅ [LLM Client] ¡Conectado al servidor quirúrgico!\n")
            
            # 3. El LLM pregunta: "¿Qué herramientas tengo disponibles?"
            print("🔍 [LLM Client] Solicitando lista de herramientas...")
            tools_response = await session.list_tools()
            for tool in tools_response.tools:
                print(f"  🛠️  {tool.name}: {tool.description.splitlines()[0]}")
                
            # 4. El LLM decide ejecutar una herramienta
            print("\n⚙️  [LLM Client] Ejecutando tool: 'list_apa_templates'...")
            result = await session.call_tool("list_apa_templates", {})
            
            print("\n📥 [LLM Client] Respuesta del servidor:")
            # Parseamos el JSON para mostrarlo bonito
            respuesta = json.loads(result.content[0].text)
            print(json.dumps(respuesta, indent=2, ensure_ascii=False))
            
            # 5. Ejemplo de inspección real (opcional)
            print("\n⚙️  [LLM Client] Ejecutando tool: 'run_xpath' para buscar títulos...")
            docx_path = "C:\\Users\\carde\\Desktop\\MUACK\\Caso_practico_u3_FINAL.docx"
            result_xpath = await session.call_tool("run_xpath", {
                "docx_path": docx_path,
                "xpath_expr": "//w:pStyle[@w:val='Ttulo2']/.."
            })
            
            respuesta_xpath = json.loads(result_xpath.content[0].text)
            print(f"\n📥 [LLM Client] ¡Encontró {respuesta_xpath['total_found']} títulos de nivel 2!")
            for item in respuesta_xpath['results'][:2]:
                print(f"  - Texto: {item['text']}")

if __name__ == "__main__":
    asyncio.run(main())
