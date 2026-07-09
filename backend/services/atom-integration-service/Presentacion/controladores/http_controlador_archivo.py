"""
Adaptador de Entrada — Controlador HTTP del AtoM Integration Service (FastAPI)
===============================================================================
Traduce las peticiones HTTP al dominio del AtoM Integration Context.

REGLAS DE ORO de este controlador:
  1. No contiene lógica de negocio: solo serializa/deserializa y delega.
  2. Depende del Puerto de Entrada (PuertoBuscadorDocumentos), nunca de la
     implementación concreta (BuscadorDocumentosUseCase).
  3. Los errores del dominio se traducen aquí a códigos HTTP apropiados.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from Aplicacion.puertos.entrada import PuertoBuscadorDocumentos

router = APIRouter(prefix="/api/v1/archive", tags=["AtoM Archive"])


@router.get(
    "/search",
    summary="Búsqueda de documentos en lenguaje natural",
    description=(
        "Realiza una búsqueda sobre el catálogo del Archivo Patrimonial UAH. "
        "En desarrollo usa el MockAdapter; en producción consulta la API REST de AtoM."
    ),
)
async def buscar_documentos(
    request: Request,
    q: str = Query(..., min_length=2, description="Consulta en lenguaje natural"),
    limit: int = Query(5, ge=1, le=20, description="Número máximo de resultados"),
) -> dict:
    """
    Endpoint de búsqueda. Delega al Puerto de Entrada, que a su vez consulta
    el repositorio inyectado (AtoM real o Mock, según la configuración).
    """
    use_case: PuertoBuscadorDocumentos = request.app.state.use_case
    resultado = await use_case.ejecutar_busqueda(query=q, limite=limit)
    return {"success": True, **resultado}


@router.get(
    "/documents/{codigo}",
    summary="Obtener detalle de un documento por código de referencia",
)
async def obtener_documento(codigo: str, request: Request) -> dict:
    """
    Obtiene el detalle completo de un documento por su código de referencia
    archivístico (ej. 'UAH-D-1027') o su slug en el sistema AtoM.
    """
    use_case: PuertoBuscadorDocumentos = request.app.state.use_case
    resultado = await use_case.obtener_detalle(codigo=codigo)

    if resultado.get("documento") is None:
        raise HTTPException(status_code=404, detail=resultado["mensaje"])

    return {"success": True, **resultado}
