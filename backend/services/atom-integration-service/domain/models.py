"""
Capa de Dominio -- Entidades Puras
===================================
Modelos Pydantic que representan los conceptos centrales del Archivo Patrimonial.
Estas entidades NO tienen dependencias de infraestructura. Son el nucleo inmutable
de la aplicacion y definen el lenguaje ubicuo del dominio (Ubiquitous Language).
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


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
    url: str = Field(..., description="URL publica del recurso digital")
    tipo_mime: TipoMIME = Field(default=TipoMIME.UNKNOWN, description="Tipo MIME del recurso")
    etiqueta: str = Field(default="", description="Texto descriptivo del recurso")


class DocumentoPatrimonial(BaseModel):
    """
    Entidad Raiz de Agregado (Aggregate Root).
    Representa un registro del Archivo Patrimonial de la UAH, mapeado
    desde el esquema Dublin Core que utiliza AtoM internamente.

    Campos clave para el sistema RAG:
    - alcance_y_contenido: texto largo necesario para generar resumenes contextuales.
    - codigo_referencia: identificador archivistico unico (ej. 'UAH-D-1027').
    """
    id: str = Field(..., description="Identificador interno del sistema")
    codigo_referencia: str = Field(default="", description="Codigo archivistico (ej. UAH-D-1027)")
    titulo: str = Field(..., description="Titulo normalizado del documento")
    anio: Optional[str] = Field(default=None, description="Anio o rango cronologico")
    url_sistema: str = Field(default="", description="URL permanente en el catalogo AtoM")
    alcance_y_contenido: str = Field(
        default="",
        description="Texto de alcance y contenido. Campo primario para el pipeline RAG."
    )
    creadores: list[str] = Field(default_factory=list, description="Autores o entidades creadoras")
    materias: list[str] = Field(default_factory=list, description="Descriptores tematicos (dc:subject)")
    cobertura: list[str] = Field(default_factory=list, description="Cobertura geografica o temporal")
    objetos_digitales: list[ObjetoDigital] = Field(
        default_factory=list,
        description="Miniaturas, escaneos y archivos digitales asociados"
    )
    relevancia: float = Field(default=0.0, description="Score de relevancia asignado por el motor de busqueda")
