"""
Chat Service — Main Entry Point
=================================
Microservicio que maneja la lógica conversacional, memoria y RAG
con Gemini y el Search Service.
Puerto: 3001
"""

import os
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🤖 Chat Service iniciando...")
    app.state.http_client = httpx.AsyncClient(timeout=30.0)
    
    # Configure Gemini
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        app.state.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        print("✅ [ChatService] Gemini API configurada.")
    else:
        app.state.gemini_model = None
        print("⚠️ [ChatService] GEMINI_API_KEY no encontrada. Funcionando en modo Mock.")
        
    print("🚀 Chat Service listo en puerto 3001")
    yield
    await app.state.http_client.aclose()
    print("👋 Chat Service cerrado")

app = FastAPI(
    title="UAH Archivo Chatbot — Chat Service",
    description="Servicio de IA conversacional",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {
        "service": "chat-service",
        "status": "healthy",
        "llm": "gemini" if os.getenv("GEMINI_API_KEY") else "none"
    }

def _build_system_prompt(docs, query):
    """Construye el prompt RAG para el asistente del archivo patrimonial"""
    context = ""
    for idx, d in enumerate(docs):
        context += f"\\n--- DOCUMENTO {idx+1} ---\\nTítulo: {d['title']}\\nDescripción: {d['description']}\\nURL: {d['href']}\\n"
        
    return f"""Eres el Asistente Experto del Archivo Patrimonial de la Universidad Alberto Hurtado.
Tu objetivo es ayudar a los usuarios a encontrar información en el archivo de manera amable, erudita y precisa.

REGLAS STRICTAS:
1. Responde SIEMPRE en español.
2. Si el usuario hace una pregunta general ("Hola", "¿Cómo estás?"), responde amablemente y ofrece tu ayuda para buscar en el archivo. No inventes documentos.
3. Si el usuario busca algo, utiliza ÚNICAMENTE el contexto de los documentos proporcionados abajo para responder.
4. NUNCA inventes información que no esté en los documentos proporcionados.
5. Si los documentos proporcionados no responden a la pregunta, dile al usuario amablemente que no encontraste información exacta sobre eso en el archivo.

CONTEXTO DEL ARCHIVO PATRIMONIAL ENCONTRADO PARA LA BÚSQUEDA "{query}":
{context}

PREGUNTA DEL USUARIO:
{query}
"""

@app.post("/api/v1/chat/message")
async def send_message(request: Request):
    """
    Recibe un mensaje del usuario, realiza RAG consultando al Search Service,
    y devuelve una respuesta usando Gemini.
    """
    data = await request.json()
    query = data.get("message", "")
    client: httpx.AsyncClient = request.app.state.http_client
    model = request.app.state.gemini_model
    
    # 1. Consultar al Search Service
    search_url = os.getenv("SEARCH_SERVICE_URL", "http://search-service:3002")
    docs = []
    try:
        search_res = await client.get(f"{search_url}/api/v1/search/query", params={"q": query, "limit": 4})
        if search_res.status_code == 200:
            search_data = search_res.json()
            docs = search_data.get("results", [])
    except Exception as e:
        print(f"❌ Error consultando Search Service: {e}")

    # 2. Generar respuesta con Gemini
    if model:
        try:
            prompt = _build_system_prompt(docs, query)
            response = await model.generate_content_async(prompt)
            ai_response = response.text
        except Exception as e:
            print(f"❌ Error llamando a Gemini: {e}")
            ai_response = "Lo siento, hubo un error de conexión con la IA. Por favor, intenta de nuevo."
    else:
        doc_titles = ", ".join([d['title'] for d in docs])
        ai_response = f"[Mock Mode] He encontrado estos documentos: {doc_titles}. Configura GEMINI_API_KEY para respuestas reales."

    return {
        "success": True,
        "response": ai_response,
        "documents": docs,
        "conversation_id": data.get("conversation_id", "default")
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3001, reload=True)
