"""
Capa de Presentación — DTOs de Respuesta HTTP
===============================================
Data Transfer Objects Pydantic que definen el contrato de la API REST
del AtoM Integration Service. Estos DTOs son los únicos artefactos del
proyecto que pueden (y deben) usar Pydantic para serialización.

SEPARACIÓN CLARA:
  - Dominio/entidades: @dataclass puro Python (sin Pydantic)
  - Presentacion/dtos: Pydantic BaseModel (serialización HTTP)
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ObjetoDigitalDTO(BaseModel):
    """DTO de salida para un recurso digital asociado a un documento."""
    url: str
    tipo_mime: str
    etiqueta: str = ""


class DocumentoPatrimonialDTO(BaseModel):
    """DTO de salida: representación completa de un documento patrimonial."""
    id: str
    codigo_referencia: str = ""
    titulo: str
    anio: Optional[str] = None
    url_sistema: str = ""
    alcance_y_contenido: str = ""
    creadores: list[str] = Field(default_factory=list)
    materias: list[str] = Field(default_factory=list)
    cobertura: list[str] = Field(default_factory=list)
    objetos_digitales: list[ObjetoDigitalDTO] = Field(default_factory=list)
    relevancia: float = 0.0


class RichCardDTO(BaseModel):
    """DTO de salida para una Rich Card del frontend."""
    id: str
    titulo: str
    codigo_referencia: str = ""
    anio: Optional[str] = None
    url: str = ""
    descripcion_corta: str = ""
    materias: list[str] = Field(default_factory=list)
    miniatura_url: Optional[str] = None
    relevancia: float = 0.0


class QuickReplyDTO(BaseModel):
    """DTO de salida para un botón de acción rápida en el frontend."""
    label: str
    value: str


class BusquedaRespuestaDTO(BaseModel):
    """DTO de salida: envoltorio completo de una respuesta de búsqueda."""
    success: bool = True
    mensaje: str
    documentos: list[DocumentoPatrimonialDTO] = Field(default_factory=list)
    rich_cards: list[RichCardDTO] = Field(default_factory=list)
    quick_replies: list[QuickReplyDTO] = Field(default_factory=list)
    total: int = 0


class DetalleDocumentoRespuestaDTO(BaseModel):
    """DTO de salida: respuesta de detalle de un documento específico."""
    success: bool = True
    mensaje: str
    documento: Optional[DocumentoPatrimonialDTO] = None
    rich_card: Optional[RichCardDTO] = None
    quick_replies: list[QuickReplyDTO] = Field(default_factory=list)
