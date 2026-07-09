"""
Adaptador de Entrada — Controlador HTTP (FastAPI)
==================================================
Traduce las peticiones HTTP del mundo exterior en llamadas al
Puerto de Entrada (BuscarContenidoUseCase).

REGLAS DE ORO de este controlador:
  1. NO contiene lógica de negocio.
  2. NO define modelos de datos (los DTOs viven en Aplicacion/dtos/).
  3. Su única responsabilidad es:
     a. Deserializar la petición HTTP (query params → Objeto de Valor Consulta).
     b. Llamar al caso de uso.
     c. Serializar la respuesta (ResultadoFusionado → DTO JSON).
     d. Traducir errores del dominio a códigos HTTP apropiados.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from Aplicacion.puertos.entrada import BuscarContenidoUseCase
from Aplicacion.dtos.busqueda_dtos import BusquedaRespuestaDTO, DocumentoRespuestaDTO
from Dominio.objetos_de_valor.busqueda import Consulta, RespuestaBusquedaDominio, ResultadoBusqueda


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


def _obtener_extractor_nlp(request: Request):
    """Extrae el NLPExtractorAdapter de app.state (puede ser None si no está configurado)."""
    return getattr(request.app.state, "nlp_extractor", None)


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
    anio: str = Query(None, description="Filtro opcional por año (ej. '1990')"),
    categoria: str = Query(None, description="Filtro opcional por categoría archivística"),
    materia: str = Query(None, description="Filtro opcional por materia o tema"),
    caso_de_uso: BuscarContenidoUseCase = Depends(_obtener_caso_de_uso),
    extractor_nlp = Depends(_obtener_extractor_nlp),
) -> BusquedaRespuestaDTO:
    """
    Endpoint principal de búsqueda híbrida.

    Traduce los parámetros HTTP al Objeto de Valor Consulta del dominio,
    ejecuta el caso de uso y serializa los resultados como DTO JSON.
    """
    # Construir diccionario de filtros HTTP explícitos
    filtros = {}
    if anio:
        filtros["anio"] = anio
    if categoria:
        filtros["categorias"] = categoria
    if materia:
        filtros["materias"] = materia

    # Extraer entidades NLP de la consulta en lenguaje natural
    filtro_nlp = None
    if extractor_nlp is not None:
        filtro_nlp = extractor_nlp.extraer_filtros(q)

    # Construir el Objeto de Valor — las invariantes del dominio se validan aquí
    try:
        consulta = Consulta(
            texto=q,
            limite=limite,
            filtros=filtros if filtros else None,
            filtro_nlp=filtro_nlp,
        )
    except ValueError as error_dominio:
        # Las invariantes del dominio se traducen a errores HTTP 422 en el adaptador
        raise HTTPException(status_code=422, detail=str(error_dominio)) from error_dominio

    # Ejecutar el caso de uso (lógica de negocio)
    respuesta_dominio: RespuestaBusquedaDominio = await caso_de_uso.ejecutar(consulta)

    # Serializar resultados al DTO de respuesta
    return BusquedaRespuestaDTO(
        exito=True,
        consulta=q,
        total=len(respuesta_dominio.resultados),
        total_corpus=respuesta_dominio.total_corpus,
        facetas=respuesta_dominio.facetas,
        resultados=[_mapear_a_dto(r) for r in respuesta_dominio.resultados],
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
