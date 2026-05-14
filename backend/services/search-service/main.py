"""
Search Service — Main Entry Point
===================================
Microservicio encargado de la búsqueda híbrida (vectores + TF-IDF)
Puerto: 3002
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from core.repository import DocumentRepository
from core.vector_store import VectorStorePort
from core.engine import SearchEngine

repository = None
vector_store = None
search_engine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🔍 Search Service iniciando...")
    
    global repository, vector_store, search_engine
    repository = DocumentRepository(data_path="data/clean_with_metadata.json")
    vector_store = VectorStorePort()
    search_engine = SearchEngine(repository, vector_store)
    
    # Ingestar a ChromaDB si es necesario (en producción se haría asincrono o en script)
    # Por ahora lo omitimos en el lifespan para no demorar el inicio.
    
    print("🚀 Search Service listo en puerto 3002")
    yield
    print("👋 Search Service cerrado")

app = FastAPI(
    title="UAH Archivo Chatbot — Search Service",
    description="Motor de búsqueda híbrido para el archivo patrimonial",
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
    return {"service": "search-service", "status": "healthy"}

@app.get("/api/v1/search/query")
async def search(
    q: str = Query(..., description="Query de búsqueda"),
    limit: int = Query(5, ge=1, le=20),
):
    """
    Realiza una búsqueda híbrida utilizando RRF sobre TF-IDF, Exact Match y ChromaDB.
    """
    if not search_engine:
        return {"success": False, "error": "Search engine not initialized"}
        
    results = search_engine.search_hybrid(q, limit=limit)
    
    # Limitar el tamaño de la respuesta para el frontend
    clean_results = []
    for r in results:
        clean_results.append({
            "id": r.get("id", r.get("slug")),
            "title": r.get("title", "Sin título"),
            "href": r.get("href", ""),
            "description": r.get("description", "")[:200] + "..." if r.get("description") else "",
            "relevance_score": r.get("relevance_score", 0)
        })
        
    return {
        "success": True,
        "query": q,
        "total": len(clean_results),
        "results": clean_results
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3002, reload=True)
