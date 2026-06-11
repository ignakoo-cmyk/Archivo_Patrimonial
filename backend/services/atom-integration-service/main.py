"""
AtoM Integration Service -- Driving Adapter (FastAPI)
========================================================
Punto de entrada HTTP del microservicio. Actua como Driving Adapter:
recibe peticiones REST, las traduce en llamadas al caso de uso, y devuelve
DTOs serializados. La inyeccion de dependencias se realiza en el lifespan.

Para desarrollo local sin AtoM, cambiar AtoMHttpAdapter por MockAtoMAdapter
en la seccion de inyeccion de dependencias (ver comentarios inline).
"""

import os
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from adapters.atom_http_adapter import AtoMHttpAdapter
from adapters.mock_adapter import MockAtoMAdapter
from application.use_cases import BuscadorDocumentosUseCase

ATOM_BASE_URL = os.getenv("ATOM_BASE_URL", "http://localhost:8081")
USE_MOCK = os.getenv("USE_MOCK_ADAPTER", "true").lower() == "true"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[atom-integration] Servicio iniciando...")

    http_client = httpx.AsyncClient(timeout=15.0)

    # -- Inyeccion de Dependencias --
    # Seleccionar adaptador segun variable de entorno.
    # En produccion, con AtoM accesible, usar USE_MOCK_ADAPTER=false
    if USE_MOCK:
        print("[atom-integration] Modo MOCK activado (sin conexion a AtoM)")
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
    title="UAH Archivo -- AtoM Integration Service",
    description="Microservicio de integracion con AtoM (Arquitectura Hexagonal)",
    version="3.0.0",
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
        "service": "atom-integration-service",
        "status": "healthy",
        "adapter": "mock" if USE_MOCK else "atom-http",
    }


@app.get("/api/v1/archive/search")
async def buscar_documentos(
    request: Request,
    q: str = Query(..., description="Consulta en lenguaje natural"),
    limit: int = Query(5, ge=1, le=20),
):
    """
    Endpoint de busqueda. Delega al caso de uso, que a su vez consulta
    el puerto inyectado (AtoM real o Mock).
    """
    use_case: BuscadorDocumentosUseCase = request.app.state.use_case
    resultado = await use_case.ejecutar_busqueda(query=q, limite=limit)
    return {"success": True, **resultado}


@app.get("/api/v1/archive/documents/{codigo}")
async def obtener_documento(codigo: str, request: Request):
    """
    Obtiene el detalle de un documento por su codigo de referencia o slug.
    """
    use_case: BuscadorDocumentosUseCase = request.app.state.use_case
    resultado = await use_case.obtener_detalle(codigo=codigo)

    if resultado.get("documento") is None:
        raise HTTPException(status_code=404, detail=resultado["mensaje"])

    return {"success": True, **resultado}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3003, reload=True)
