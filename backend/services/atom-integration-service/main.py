"""
AtoM Integration Service — Main Entry Point
=============================================
Microservicio responsable de comunicarse con la API de AtoM
(Access to Memory) y traducir los datos al formato del dominio (ACL).
Puerto: 3003
"""

import os
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

ATOM_BASE_URL = os.getenv("ATOM_BASE_URL", "http://localhost:8081")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("📚 AtoM Integration Service iniciando...")
    app.state.http_client = httpx.AsyncClient(timeout=15.0)
    print("🚀 AtoM Integration Service listo en puerto 3003")
    yield
    await app.state.http_client.aclose()
    print("👋 AtoM Integration Service cerrado")

app = FastAPI(
    title="UAH Archivo Chatbot — AtoM Integration",
    description="Anti-Corruption Layer para AtoM",
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
    return {"service": "atom-integration-service", "status": "healthy", "atom_url": ATOM_BASE_URL}

@app.get("/api/v1/archive/documents/{slug}")
async def get_document(slug: str):
    """Obtiene un documento directo desde AtoM"""
    client: httpx.AsyncClient = app.state.http_client
    try:
        res = await client.get(f"{ATOM_BASE_URL}/api/informationobjects/{slug}")
        res.raise_for_status()
        data = res.json()
        
        # Anti-Corruption Layer (mapeo simplificado)
        return {
            "success": True,
            "document": {
                "id": data.get("id", slug),
                "title": data.get("title", data.get("dc:title", "Sin título")),
                "slug": slug,
                "href": data.get("url", f"https://archivopatrimonial.uahurtado.cl/{slug}"),
                "description": data.get("scope_and_content", data.get("dc:description", "")),
                "date": data.get("dates", data.get("dc:date", "")),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Documento no encontrado o error en AtoM: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3003, reload=True)
