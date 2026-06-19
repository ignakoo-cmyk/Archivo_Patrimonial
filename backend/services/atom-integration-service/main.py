"""
AtoM Integration Service — Driving Adapter (FastAPI)
========================================================
Punto de entrada HTTP del microservicio. Actúa como Composition Root:
La inyección de dependencias se realiza en el lifespan.

Para desarrollo local sin AtoM, cambiar AtoMHttpAdapter por MockAtoMAdapter
en la sección de inyección de dependencias (ver comentarios inline).
"""

import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from Infraestructura.adaptadores_salida.atom_http_adaptador import AtoMHttpAdapter
from Infraestructura.adaptadores_salida.mock_adaptador import MockAtoMAdapter
from Aplicacion.casos_de_uso.buscador_documentos import BuscadorDocumentosUseCase
from Presentacion.controladores.http_controlador_archivo import router as router_archivo

ATOM_BASE_URL = os.getenv("ATOM_BASE_URL", "http://localhost:8081")
USE_MOCK = os.getenv("USE_MOCK_ADAPTER", "true").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[atom-integration] Servicio iniciando...")

    http_client = httpx.AsyncClient(timeout=15.0)

    # ── Inyección de Dependencias ──
    # Seleccionar adaptador según variable de entorno.
    # En producción, con AtoM accesible, usar USE_MOCK_ADAPTER=false
    if USE_MOCK:
        print("[atom-integration] Modo MOCK activado (sin conexión a AtoM)")
        adapter = MockAtoMAdapter()
    else:
        print(f"[atom-integration] Conectando a AtoM en {ATOM_BASE_URL}")
        adapter = AtoMHttpAdapter(base_url=ATOM_BASE_URL, http_client=http_client)

    # Inyectar el caso de uso con el adaptador seleccionado
    app.state.use_case = BuscadorDocumentosUseCase(repositorio=adapter)
    app.state.http_client = http_client

    print("[atom-integration] Servicio listo en puerto 3003")
    yield
    await http_client.aclose()
    print("[atom-integration] Servicio cerrado")


app = FastAPI(
    title="UAH Archivo — AtoM Integration Service",
    description="Microservicio de integración con AtoM (Arquitectura Hexagonal)",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router_archivo)


@app.get("/health", tags=["Infraestructura"])
async def health():
    return {
        "service": "atom-integration-service",
        "status": "healthy",
        "adapter": "mock" if USE_MOCK else "atom-http",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3003, reload=True)
