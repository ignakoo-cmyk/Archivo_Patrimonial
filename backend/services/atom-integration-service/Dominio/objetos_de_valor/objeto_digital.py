"""
Capa de Dominio — Objetos de Valor
===================================
Modelos Pydantic inmutables que representan conceptos dependientes de la entidad.
"""

from enum import Enum
from pydantic import BaseModel, Field


class TipoMIME(str, Enum):
    """Tipos MIME soportados para objetos digitales del archivo."""
    IMAGE_JPEG = "image/jpeg"
    IMAGE_PNG = "image/png"
    APPLICATION_PDF = "application/pdf"
    AUDIO_MPEG = "audio/mpeg"
    VIDEO_MP4 = "video/mp4"
    TEXT_PLAIN = "text/plain"
    UNKNOWN = "application/octet-stream"


class ObjetoDigital(BaseModel):
    """
    Value Object que representa un recurso digital asociado a un documento
    patrimonial (miniatura, escaneo, archivo de audio, etc.).
    """
    url: str = Field(..., description="URL pública del recurso digital")
    tipo_mime: TipoMIME = Field(default=TipoMIME.UNKNOWN, description="Tipo MIME del recurso")
    etiqueta: str = Field(default="", description="Texto descriptivo del recurso")
