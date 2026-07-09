"""
Chat Service — Entry Point (Composition Root)
=============================================
Único punto de ensamblado de la aplicación. Aquí se instancian los
adaptadores concretos y se construye el grafo de dependencias completo.

Decisiones de infraestructura tomadas aquí (cambiar una línea = cambiar tecnología):
  - LLM:         GeminiAdapter              → cambiar por OpenAIAdapter sin tocar el dominio.
  - Búsqueda:    SearchServiceHttpAdapter   → cambiar por MockBusquedaAdapter en tests.
  - Sesiones:    InMemorySesionRepositorio  → cambiar por RedisSesionRepositorio en producción.
  - Prompt:      PROMPT_ACADEMICO_UAH       → cambiar por otro PromptTemplate para A/B testing.
"""

import os
import traceback
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── Adaptadores de Infraestructura ────────────────────────────────────────────
from Presentacion.controladores.http_controlador_chat import router as router_chat
from Infraestructura.adaptadores_salida.gemini_adaptador import GeminiAdapter
from Infraestructura.adaptadores_salida.servicio_busqueda_adaptador import SearchServiceHttpAdapter
from Infraestructura.adaptadores_salida.sesion_en_memoria_adaptador import InMemorySesionRepositorio

# ── Dominio (código puro) ─────────────────────────────────────────────────────
from Dominio.servicios.orquestador_chat import ChatOrchestratorService
from Dominio.objetos_de_valor.prompt_template import PROMPT_ACADEMICO_UAH


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Composition Root: ensambla todos los adaptadores y el servicio de dominio."""
    print("🤖 [chat-service] Iniciando composición de dependencias...")

    # ── 1. Infraestructura compartida ─────────────────────────────────────────
    cliente_http = httpx.AsyncClient(timeout=30.0)

    # ── 2. Adaptadores de Salida ──────────────────────────────────────────────
    gemini = GeminiAdapter(api_key=os.getenv("GEMINI_API_KEY", ""))

    busqueda = SearchServiceHttpAdapter(
        base_url=os.getenv("SEARCH_SERVICE_URL", "http://search-service:3002"),
        cliente_http=cliente_http,
    )

    # ── 3. Repositorio de Sesiones (InMemory → Redis en producción) ───────────
    sesion_repositorio = InMemorySesionRepositorio()

    # ── 4. Servicio de Dominio ensamblado con todas sus dependencias ──────────
    app.state.orquestador = ChatOrchestratorService(
        modelo_lenguaje=gemini,
        servicio_busqueda=busqueda,
        prompt_template=PROMPT_ACADEMICO_UAH,
    )

    # ── 5. Repositorio de sesiones disponible para el controlador ─────────────
    app.state.sesion_repositorio = sesion_repositorio
    app.state.cliente_http = cliente_http

    print("✅ [chat-service] Listo en puerto 3001.")
    yield

    await cliente_http.aclose()
    print("👋 [chat-service] Cerrado.")


# ── Configuración FastAPI ─────────────────────────────────────────────────────
app = FastAPI(
    title="UAH Archivo Patrimonial — Chat Service",
    description=(
        "Asistente conversacional con RAG sobre el Archivo Patrimonial UAH. "
        "Arquitectura Hexagonal + DDD con Bounded Contexts (Chat y Search)."
    ),
    version="3.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Adaptadores de Entrada (Routers) ─────────────────────────────────────────
app.include_router(router_chat)


@app.get("/health", tags=["Infraestructura"])
async def health():
    return {
        "servicio": "chat-service",
        "estado": "saludable",
        "version": "3.1.0",
        "arquitectura": "hexagonal-ddd-bounded-contexts",
        "llm": "gemini-2.5-flash" if os.getenv("GEMINI_API_KEY") else "sin-llm",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3001, reload=True)
