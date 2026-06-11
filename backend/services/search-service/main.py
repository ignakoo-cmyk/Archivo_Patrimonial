"""
Entry Point — Composición de la Aplicación (Composition Root)
==============================================================
Este es el ÚNICO lugar donde todas las capas se ensamblan y las
dependencias concretas se conectan a los puertos abstractos.

Aquí se decide:
  - Qué almacén vectorial usar (ChromaDB hoy, otro mañana).
  - Qué motor léxico usar (TF-IDF hoy, BM25 mañana).
  - Qué repositorio usar (JSON local hoy, API AtoM en producción).

Cambiar cualquiera de esas decisiones = cambiar una sola línea aquí.
El dominio, los puertos y todos los demás adaptadores permanecen intactos.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ── Adaptadores de Infraestructura (código que depende de librerías) ──────────
from adapters.salida.chromadb_adapter import ChromaDBAdapter
from adapters.salida.tfidf_adapter import TFIDFAdapter
from adapters.salida.static_json_adapter import StaticJsonRepositoryAdapter
from adapters.entrada.http_controller import router as router_busqueda

# ── Capa de Aplicación y Dominio (código puro) ───────────────────────────────
from application.casos_de_uso.buscar_contenido import BuscarContenidoService
from domain.search_context.services import GestorBusqueda


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan de FastAPI: Composition Root.

    Se ejecuta UNA sola vez al iniciar la aplicación.
    Aquí se instancian todos los adaptadores y se ensambla el grafo
    completo de dependencias (dominio ← puertos ← adaptadores).
    """
    print("🔍 [search-service] Iniciando composición de dependencias...")

    # ── 1. Instanciar Adaptadores de Salida ───────────────────────────────────
    repositorio = StaticJsonRepositoryAdapter(
        ruta_json=os.getenv("DATA_PATH", "data/clean_with_metadata.json")
    )

    chroma_adapter = ChromaDBAdapter(
        host=os.getenv("CHROMA_HOST", "chromadb"),
        puerto=int(os.getenv("CHROMA_PORT", "8000")),
    )

    tfidf_adapter = TFIDFAdapter()
    # Construir índice léxico con todos los documentos del repositorio
    tfidf_adapter.construir_indice(repositorio.obtener_todos())

    # ── 2. Ensamblar el Servicio de Dominio ───────────────────────────────────
    # GestorBusqueda recibe los Puertos (abstracciones), no los adaptadores concretos.
    # Python resuelve esto porque los adaptadores implementan las interfaces ABC.
    gestor = GestorBusqueda(
        almacen_vectorial=chroma_adapter,
        indice_lexico=tfidf_adapter,
        repositorio=repositorio,
    )

    # ── 3. Instanciar el Caso de Uso y alojar en el estado de la app ──────────
    app.state.caso_de_uso = BuscarContenidoService(gestor=gestor)

    print("✅ [search-service] Listo en puerto 3002.")
    yield
    print("👋 [search-service] Cerrando.")


# ── Configuración de la aplicación FastAPI ────────────────────────────────────
app = FastAPI(
    title="UAH Archivo Patrimonial — Search Service",
    description=(
        "Motor de búsqueda híbrida (RRF sobre ChromaDB + TF-IDF + Coincidencia Exacta). "
        "Arquitectura Hexagonal / Puertos y Adaptadores + DDD."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ── Registro del Router (Adaptador de Entrada) ────────────────────────────────
app.include_router(router_busqueda)


@app.get("/health", tags=["Infraestructura"])
async def health_check():
    """Endpoint de verificación de estado para Docker y monitoreo."""
    return {
        "servicio": "search-service",
        "estado": "saludable",
        "version": "2.0.0",
        "arquitectura": "hexagonal",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3002, reload=True)
