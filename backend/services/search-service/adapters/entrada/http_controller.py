"""
Adaptador de Entrada — Controlador HTTP (FastAPI)
==================================================
Traduce las peticiones HTTP del mundo exterior en llamadas al
Puerto de Entrada (BuscarContenidoUseCase).

REGLA DE ORO: Este controlador NO contiene lógica de negocio.
Su única responsabilidad es:
  1. Deserializar la petición HTTP (query params → Objeto de Valor Consulta).
  2. Llamar al caso de uso.
  3. Serializar la respuesta (ResultadoFusionado → DTO JSON).
  4. Traducir errores del dominio a códigos HTTP apropiados.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from application.puertos.entrada import BuscarContenidoUseCase
from domain.search_context.models import Consulta, ResultadoBusqueda


# ─────────────────────────────────────────────────────────────
# DTOs de Respuesta (Data Transfer Objects)
# Estas clases viven en el adaptador — NO son entidades de dominio.
# Su forma puede cambiar sin afectar el dominio.
# ─────────────────────────────────────────────────────────────

class DocumentoRespuestaDTO(BaseModel):
    """DTO de salida: representación serializable de un único resultado."""
    id: str
    titulo: str
    descripcion_corta: str
    url_catalogo: str
    puntuacion_rrf: float


class BusquedaRespuestaDTO(BaseModel):
    """DTO de salida: envoltura completa de la respuesta de búsqueda."""
    exito: bool
    consulta: str
    total: int
    resultados: list[DocumentoRespuestaDTO]


# ─────────────────────────────────────────────────────────────
# Router de FastAPI
# ─────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/v1/search", tags=["Búsqueda Híbrida"])


def _obtener_caso_de_uso(request: Request) -> BuscarContenidoUseCase:
    """
    Función de dependencia de FastAPI.

    Extrae el caso de uso previamente inyectado en el lifespan de la app
    y almacenado en app.state. Esto permite:
    - Reutilizar la misma instancia en toda la vida del servidor.
    - Mockear el caso de uso en tests de integración sin levantar infraestructura.
    """
    return request.app.state.caso_de_uso


@router.get(
    "/query",
    response_model=BusquedaRespuestaDTO,
    summary="Búsqueda híbrida de documentos patrimoniales",
    description=(
        "Ejecuta una búsqueda híbrida (RRF sobre ChromaDB + TF-IDF + Coincidencia Exacta) "
        "sobre el Archivo Patrimonial UAH. Retorna documentos ordenados por relevancia compuesta."
    ),
)
async def buscar(
    q: str = Query(
        ...,
        min_length=2,
        description="Consulta en lenguaje natural (mínimo 2 caracteres)",
    ),
    limite: int = Query(
        5,
        ge=1,
        le=20,
        description="Número máximo de resultados a retornar (entre 1 y 20)",
    ),
    caso_de_uso: BuscarContenidoUseCase = Depends(_obtener_caso_de_uso),
) -> BusquedaRespuestaDTO:
    """
    Endpoint principal de búsqueda híbrida.

    Traduce los parámetros HTTP al Objeto de Valor Consulta del dominio,
    ejecuta el caso de uso y serializa los resultados como DTO JSON.
    """
    # Construir el Objeto de Valor — las invariantes del dominio se validan aquí
    try:
        consulta = Consulta(texto=q, limite=limite)
    except ValueError as error_dominio:
        # Las invariantes del dominio se traducen a errores HTTP 422 en el adaptador
        raise HTTPException(status_code=422, detail=str(error_dominio)) from error_dominio

    # Ejecutar el caso de uso (lógica de negocio)
    resultados: list[ResultadoBusqueda] = caso_de_uso.ejecutar(consulta)

    # Serializar resultados al DTO de respuesta
    return BusquedaRespuestaDTO(
        exito=True,
        consulta=q,
        total=len(resultados),
        resultados=[_mapear_a_dto(r) for r in resultados],
    )


# ─────────────────────────────────────────────────────────────
# Funciones de mapeo privadas del adaptador
# ─────────────────────────────────────────────────────────────

def _mapear_a_dto(resultado: ResultadoBusqueda) -> DocumentoRespuestaDTO:
    """
    Convierte una entidad de dominio ResultadoFusionado al DTO de respuesta HTTP.
    Responsabilidad exclusiva del adaptador de entrada.
    """
    doc = resultado.documento
    descripcion_corta = (
        doc.descripcion[:200] + "…"
        if len(doc.descripcion) > 200
        else doc.descripcion
    )
    return DocumentoRespuestaDTO(
        id=doc.id,
        titulo=doc.titulo,
        descripcion_corta=descripcion_corta,
        url_catalogo=doc.url_catalogo,
        puntuacion_rrf=resultado.puntuacion_rrf,
    )
