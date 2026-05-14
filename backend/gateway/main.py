"""
API Gateway — Main Entry Point
================================

Gateway centralizado para ruteo a microservicios del Chatbot del Archivo UAH.
Puerto: 3000
"""

import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

SERVICES = {
    "chat": os.getenv("CHAT_SERVICE_URL", "http://chat-service:3001"),
    "search": os.getenv("SEARCH_SERVICE_URL", "http://search-service:3002"),
    "archive": os.getenv("ATOM_SERVICE_URL", "http://atom-integration:3003"),
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🌐 API Gateway iniciando...")
    app.state.http_client = httpx.AsyncClient(timeout=30.0)
    print("🚀 API Gateway listo en puerto 3000")
    yield
    await app.state.http_client.aclose()
    print("👋 API Gateway cerrado")


app = FastAPI(
    title="UAH Archivo Chatbot — API Gateway",
    description="Gateway unificado para la interfaz de búsqueda",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"service": "api-gateway", "status": "healthy"}


async def _proxy_request(request: Request, service_key: str, path: str):
    if service_key not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Servicio no encontrado: {service_key}")

    client: httpx.AsyncClient = request.app.state.http_client
    target_url = f"{SERVICES[service_key]}/{path}"

    headers = dict(request.headers)
    headers.pop("host", None)

    try:
        body = await request.body()
        req = client.build_request(
            method=request.method,
            url=target_url,
            content=body,
            headers=headers,
            params=dict(request.query_params)
        )
        response = await client.send(req, stream=True)
        
        # Si es Server-Sent Events (SSE) para el streaming del chat
        if response.headers.get("content-type") == "text/event-stream":
            return StreamingResponse(
                response.aiter_raw(),
                media_type="text/event-stream",
                background=response.aclose
            )
            
        await response.aread()
        return JSONResponse(
            content=response.json() if response.content else None,
            status_code=response.status_code,
        )
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail=f"Servicio '{service_key}' no disponible")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.api_route("/api/v1/chat/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_chat(request: Request, path: str):
    return await _proxy_request(request, "chat", f"api/v1/chat/{path}")

@app.api_route("/api/v1/search/{path:path}", methods=["GET", "POST"])
async def proxy_search(request: Request, path: str):
    return await _proxy_request(request, "search", f"api/v1/search/{path}")

@app.api_route("/api/v1/archive/{path:path}", methods=["GET"])
async def proxy_archive(request: Request, path: str):
    return await _proxy_request(request, "archive", f"api/v1/archive/{path}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)
