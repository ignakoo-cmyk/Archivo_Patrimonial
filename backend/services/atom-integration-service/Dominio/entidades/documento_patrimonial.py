"""
Capa de Dominio — Entidad de Dominio: DocumentoPatrimonial
============================================================
Entidad Raíz de Agregado (Aggregate Root).
Representa un registro del Archivo Patrimonial de la UAH, mapeado
desde el esquema Dublin Core que utiliza AtoM internamente.

Campos clave para el sistema RAG:
- alcance_y_contenido: texto largo necesario para generar resúmenes contextuales.
- codigo_referencia: identificador archivístico único (ej. 'UAH-D-1027').
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from Dominio.objetos_de_valor.objeto_digital import ObjetoDigital


class DocumentoPatrimonial(BaseModel):
    """
    Entidad Raíz de Agregado (Aggregate Root).
    Representa un registro del Archivo Patrimonial de la UAH.
    """
    id: str = Field(..., description="Identificador interno del sistema")
    codigo_referencia: str = Field(default="", description="Código archivístico (ej. UAH-D-1027)")
    titulo: str = Field(..., description="Título normalizado del documento")
    anio: Optional[str] = Field(default=None, description="Año o rango cronológico")
    url_sistema: str = Field(default="", description="URL permanente en el catálogo AtoM")
    alcance_y_contenido: str = Field(
        default="",
        description="Texto de alcance y contenido. Campo primario para el pipeline RAG."
    )
    creadores: list[str] = Field(default_factory=list, description="Autores o entidades creadoras")
    materias: list[str] = Field(default_factory=list, description="Descriptores temáticos (dc:subject)")
    cobertura: list[str] = Field(default_factory=list, description="Cobertura geográfica o temporal")
    objetos_digitales: list[ObjetoDigital] = Field(
        default_factory=list,
        description="Miniaturas, escaneos y archivos digitales asociados"
    )
    relevancia: float = Field(default=0.0, description="Score de relevancia asignado por el motor de búsqueda")
