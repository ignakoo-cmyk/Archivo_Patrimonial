"""
Controladores HTTP — Atom Integration
======================================
Define los endpoints REST para la integración con AtoM.
"""

from fastapi import APIRouter, HTTPException, Query, Request

from Aplicacion.casos_de_uso.buscador_documentos import BuscadorDocumentosUseCase

router = APIRouter(prefix="/api/v1/archive", tags=["AtoM Archive"])


@router.get("/search")
async def buscar_documentos(
    request: Request,
    q: str = Query(..., description="Consulta en lenguaje natural"),
    limit: int = Query(5, ge=1, le=20),
):
    """
    Endpoint de búsqueda. Delega al caso de uso, que a su vez consulta
    el puerto inyectado (AtoM real o Mock).
    """
    use_case: BuscadorDocumentosUseCase = request.app.state.use_case
    resultado = await use_case.ejecutar_busqueda(query=q, limite=limit)
    return {"success": True, **resultado}


@router.get("/documents/{codigo}")
async def obtener_documento(codigo: str, request: Request):
    """
    Obtiene el detalle de un documento por su código de referencia o slug.
    """
    use_case: BuscadorDocumentosUseCase = request.app.state.use_case
    resultado = await use_case.obtener_detalle(codigo=codigo)

    if resultado.get("documento") is None:
        raise HTTPException(status_code=404, detail=resultado["mensaje"])

    return {"success": True, **resultado}
