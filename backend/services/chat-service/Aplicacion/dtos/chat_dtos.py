"""
DTOs del Chat Service — Objetos de Transferencia de Datos
==========================================================
Clases Pydantic que definen el formato de entrada/salida de la API.
Estas NO son entidades de dominio; son contratos de la capa de aplicación
que pueden cambiar sin afectar la lógica de negocio.
"""

from pydantic import BaseModel, Field, AliasChoices


class MensajeEntradaDTO(BaseModel):
    """DTO de entrada: petición de chat del usuario. Soporta tanto inglés como español."""
    message: str = Field(..., validation_alias=AliasChoices("message", "mensaje"))
    conversation_id: str = Field("default", validation_alias=AliasChoices("conversation_id", "id_conversacion"))


class DocumentoReferenciaDTO(BaseModel):
    """DTO de salida para las fuentes utilizadas en RAG."""
    title: str
    href: str
    relevance_score: float = 0.0
    description: str = ""


class MensajeRespuestaDTO(BaseModel):
    """DTO de salida: respuesta del asistente en el formato esperado por el frontend."""
    success: bool
    response: str
    conversation_id: str
    documents: list[DocumentoReferenciaDTO] = []
    rich_cards: list[dict] = []
    quick_replies: list[dict] = []
