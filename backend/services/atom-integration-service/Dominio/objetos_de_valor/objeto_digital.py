"""
Capa de Dominio — Objeto de Valor: ObjetoDigital
=================================================
Representa un recurso digital asociado a un documento patrimonial
(miniatura, escaneo, archivo de audio, etc.).

REGLA DE ORO: Solo Python estándar. Sin imports de Pydantic, FastAPI
ni ninguna librería de terceros. Esta clase debe ser testeable de forma
aislada, sin dependencias externas.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TipoMIME(str, Enum):
    """Tipos MIME soportados para objetos digitales del archivo patrimonial UAH."""
    IMAGE_JPEG          = "image/jpeg"
    IMAGE_PNG           = "image/png"
    APPLICATION_PDF     = "application/pdf"
    AUDIO_MPEG          = "audio/mpeg"
    VIDEO_MP4           = "video/mp4"
    TEXT_PLAIN          = "text/plain"
    UNKNOWN             = "application/octet-stream"


@dataclass(frozen=True)
class ObjetoDigital:
    """
    Objeto de Valor inmutable que representa un recurso digital
    asociado a un documento patrimonial (miniatura, escaneo, audio, etc.).

    Es frozen=True porque un objeto digital no se modifica una vez creado:
    su URL, tipo y etiqueta son propiedades permanentes del registro archivístico.
    """
    url: str
    tipo_mime: TipoMIME = TipoMIME.UNKNOWN
    etiqueta: str = ""

    def __post_init__(self) -> None:
        if not self.url or not self.url.strip():
            raise ValueError("ObjetoDigital requiere una URL no vacía.")

    @property
    def es_imagen(self) -> bool:
        """Indica si el recurso es una imagen (útil para seleccionar miniaturas)."""
        return self.tipo_mime.value.startswith("image/")

    @property
    def es_audio(self) -> bool:
        """Indica si el recurso es un archivo de audio."""
        return self.tipo_mime.value.startswith("audio/")
