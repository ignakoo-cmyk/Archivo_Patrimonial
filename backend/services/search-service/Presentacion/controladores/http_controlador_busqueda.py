"""
Adaptador de Entrada — Controlador HTTP (FastAPI)
==================================================
Traduce las peticiones HTTP del mundo exterior en llamadas al
Puerto de Entrada (BuscarContenidoUseCase).

REGLAS DE ORO de este controlador:
  1. NO contiene lógica de negocio.
  2. NO define modelos de datos (los DTOs viven en Aplicacion/dtos/).
  3. Su única responsabilidad es:
     a. Deserializar la petición HTTP (query params o body JSON → Objeto de Valor Consulta).
     b. Llamar al caso de uso.
     c. Serializar la respuesta (ResultadoFusionado → DTO JSON).
     d. Traducir errores del dominio a códigos HTTP apropiados.

Endpoints expuestos:
  - GET  /api/v1/search/query?q=...    → búsqueda clásica con query params
  - POST /api/v1/search                → búsqueda moderna con body JSON {"query": "..."}
    (recomendado para Locust, k6 y clientes REST)
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from Aplicacion.puertos.entrada import BuscarContenidoUseCase
from Aplicacion.dtos.busqueda_dtos import BusquedaRespuestaDTO, DocumentoRespuestaDTO
from Dominio.objetos_de_valor.busqueda import Consulta, RespuestaBusquedaDominio, ResultadoBusqueda


# ─────────────────────────────────────────────────────────────
# Router de FastAPI
# ─────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/v1/search", tags=["Búsqueda Híbrida"])


# ─────────────────────────────────────────────────────────────
# DTO de entrada para el endpoint POST (body JSON)
# ─────────────────────────────────────────────────────────────

class BusquedaRequestDTO(BaseModel):
    """
    DTO de entrada para la búsqueda via POST con body JSON.
    Compatible con clientes REST modernos y herramientas de prueba de carga (Locust, k6).
    """
    query: str = Field(..., min_length=2, description="Consulta en lenguaje natural")
    limite: int = Field(5, ge=1, le=20, description="Número máximo de resultados")
    anio: str | None = Field(None, description="Filtro opcional por año")
    categoria: str | None = Field(None, description="Filtro opcional por categoría")
    materia: str | None = Field(None, description="Filtro opcional por materia")


# ─────────────────────────────────────────────────────────────
# Funciones de dependencia de FastAPI
# ─────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────
# Función auxiliar interna para construir y ejecutar la consulta
# ─────────────────────────────────────────────────────────────

async def _ejecutar_busqueda(
    texto: str,
    limite: int,
    anio: str | None,
    categoria: str | None,
    materia: str | None,
    caso_de_uso: BuscarContenidoUseCase,
    extractor_nlp,
) -> BusquedaRespuestaDTO:
    """
    Lógica compartida entre GET y POST: construye la Consulta de dominio,
    ejecuta el caso de uso y serializa los resultados.
    """
    filtros = {}
    if anio:
        filtros["anio"] = anio
    if categoria:
        filtros["categorias"] = categoria
    if materia:
        filtros["materias"] = materia

    filtro_nlp = None
    if extractor_nlp is not None:
        filtro_nlp = extractor_nlp.extraer_filtros(texto)

    try:
        consulta = Consulta(
            texto=texto,
            limite=limite,
            filtros=filtros if filtros else None,
            filtro_nlp=filtro_nlp,
        )
    except ValueError as error_dominio:
        raise HTTPException(status_code=422, detail=str(error_dominio)) from error_dominio

    respuesta_dominio: RespuestaBusquedaDominio = await caso_de_uso.ejecutar(consulta)

    return BusquedaRespuestaDTO(
        exito=True,
        consulta=texto,
        total=len(respuesta_dominio.resultados),
        total_corpus=respuesta_dominio.total_corpus,
        facetas=respuesta_dominio.facetas,
        resultados=[_mapear_a_dto(r) for r in respuesta_dominio.resultados],
    )


# ─────────────────────────────────────────────────────────────
# Endpoints HTTP
# ─────────────────────────────────────────────────────────────

@router.get(
    "/query",
    response_model=BusquedaRespuestaDTO,
    summary="Búsqueda híbrida (GET con query params)",
    description=(
        "Ejecuta una búsqueda híbrida (RRF sobre ChromaDB + TF-IDF + Coincidencia Exacta) "
        "sobre el Archivo Patrimonial UAH. Retorna documentos ordenados por relevancia compuesta."
    ),
)
async def buscar_get(
    q: str = Query(..., min_length=2, description="Consulta en lenguaje natural"),
    limite: int = Query(5, ge=1, le=20, description="Número máximo de resultados"),
    anio: str = Query(None, description="Filtro opcional por año (ej. '1990')"),
    categoria: str = Query(None, description="Filtro opcional por categoría archivística"),
    materia: str = Query(None, description="Filtro opcional por materia o tema"),
    caso_de_uso: BuscarContenidoUseCase = Depends(_obtener_caso_de_uso),
    extractor_nlp=Depends(_obtener_extractor_nlp),
) -> BusquedaRespuestaDTO:
    """Búsqueda híbrida con query params. Ej: GET /api/v1/search/query?q=decretos"""
    return await _ejecutar_busqueda(q, limite, anio, categoria, materia, caso_de_uso, extractor_nlp)


@router.post(
    "",
    response_model=BusquedaRespuestaDTO,
    summary="Búsqueda híbrida (POST con body JSON)",
    description=(
        "Endpoint POST equivalente al GET /query pero usando body JSON. "
        "Recomendado para clientes REST y pruebas de carga (Locust, k6, etc.). "
        "Acepta: {\"query\": \"...\", \"limite\": 5, \"anio\": null, \"categoria\": null, \"materia\": null}"
    ),
)
async def buscar_post(
    body: BusquedaRequestDTO,
    caso_de_uso: BuscarContenidoUseCase = Depends(_obtener_caso_de_uso),
    extractor_nlp=Depends(_obtener_extractor_nlp),
) -> BusquedaRespuestaDTO:
    """
    Búsqueda híbrida con body JSON.

    Corrige el mismatch de contrato detectado en pruebas de carga con Locust:
    el cliente enviaba POST con body JSON pero el servicio solo aceptaba GET con query params.
    Ambos endpoints delegan al mismo caso de uso, garantizando comportamiento idéntico.
    """
    return await _ejecutar_busqueda(
        body.query, body.limite, body.anio, body.categoria, body.materia,
        caso_de_uso, extractor_nlp,
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
