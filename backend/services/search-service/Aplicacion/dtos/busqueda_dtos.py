"""
Capa de Aplicación — DTOs de Búsqueda (Data Transfer Objects)
==============================================================
Define los contratos de datos de la API REST del Search Service.

Separar los DTOs del controlador HTTP garantiza:
  - El controlador solo se ocupa de rutear peticiones (SRP).
  - Los DTOs pueden ser reutilizados por otros adaptadores de entrada
    (CLI, gRPC, WebSocket) sin duplicar las definiciones.
  - El contrato de la API puede evolucionar independientemente del
    código de ruteo.

NOTA: Pydantic está justificado aquí (capa de Aplicación/Presentación).
No debe usarse en la capa de Dominio.
"""

from __future__ import annotations

from pydantic import BaseModel


class DocumentoRespuestaDTO(BaseModel):
    """DTO de salida: representación serializable de un único resultado de búsqueda."""
    id: str
    titulo: str
    descripcion_corta: str
    url_catalogo: str
    puntuacion_rrf: float


class BusquedaRespuestaDTO(BaseModel):
    """DTO de salida: envoltura completa de la respuesta de búsqueda híbrida."""
    exito: bool
    consulta: str
    total: int                          # Documentos retornados en la página actual
    total_corpus: int                   # Total en el corpus filtrado por NLP
    facetas: dict[str, list[str]]       # Sugerencias dinámicas para refinamiento conversacional
    resultados: list[DocumentoRespuestaDTO]
