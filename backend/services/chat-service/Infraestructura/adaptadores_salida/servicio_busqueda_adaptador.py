"""
Adaptador de Salida — Search Service HTTP
==========================================
Implementa ServicioBusquedaPort comunicándose con el search-service via HTTP.
Encapsula toda la lógica de httpx, serialización JSON y manejo de errores de red.
"""

from __future__ import annotations

import httpx

from Dominio.puertos.puertos_salida import ServicioBusquedaPort
from Dominio.entidades.documento_patrimonial import DocumentoPatrimonial


class SearchServiceHttpAdapter(ServicioBusquedaPort):
    """
    Adaptador de Salida concreto para el search-service via HTTP REST.
    Implementa el contrato ServicioBusquedaPort.
    """

    def __init__(self, base_url: str, cliente_http: httpx.AsyncClient) -> None:
        """
        Args:
            base_url:     URL base del search-service (ej. 'http://search-service:3002').
            cliente_http: Cliente httpx asíncrono compartido (inyectado desde lifespan).
        """
        self._base_url = base_url.rstrip("/")
        self._cliente = cliente_http

    async def buscar_documentos_relevantes(
        self, consulta: str, limite: int = 5
    ) -> tuple[list[DocumentoPatrimonial], int, dict[str, list[str]]]:
        """
        Llama al endpoint /api/v1/search/query del search-service y
        mapea la respuesta JSON al tipo de dominio DocumentoPatrimonial.
        """
        try:
            respuesta = await self._cliente.get(
                f"{self._base_url}/api/v1/search/query",
                params={"q": consulta, "limite": limite},
            )
            respuesta.raise_for_status()
            datos = respuesta.json()
        except Exception as error:
            print(f"❌ [SearchServiceHttpAdapter] Error al consultar búsqueda: {error}")
            return [], 0, {}

        documentos = [
            self._mapear_resultado(r)
            for r in datos.get("resultados", [])
            if r.get("id") and r.get("titulo")
        ]
        
        total_corpus = datos.get("total_corpus", 0)
        facetas = datos.get("facetas", {})
        
        return documentos, total_corpus, facetas

    @staticmethod
    def _mapear_resultado(raw: dict) -> DocumentoPatrimonial:
        """Traduce el DTO JSON del search-service a la entidad de dominio local."""
        return DocumentoPatrimonial(
            id=raw.get("id", ""),
            titulo=raw.get("titulo", "Sin título"),
            descripcion=raw.get("descripcion_corta", ""),
            url_catalogo=raw.get("url_catalogo", ""),
            puntuacion_relevancia=raw.get("puntuacion_rrf", 0.0),
        )
