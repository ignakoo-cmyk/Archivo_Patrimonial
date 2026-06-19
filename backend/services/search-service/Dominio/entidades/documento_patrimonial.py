"""
Search Context — Entidad de Dominio: DocumentoPatrimonial
==========================================================
Entidad raíz de agregado del Search Context.
Representa un registro archivístico del Archivo Patrimonial UAH,
mapeado desde el esquema Dublin Core de AtoM o el JSON de metadatos.

REGLA DE ORO: Sin imports de FastAPI, ChromaDB, scikit-learn ni ningún framework.
Solo Python estándar. Estas clases son el lenguaje ubicuo del dominio de búsqueda.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DocumentoPatrimonial:
    """
    Entidad raíz de agregado del Search Context.
    Representa un registro archivístico del Archivo Patrimonial UAH,
    mapeado desde el esquema Dublin Core de AtoM o el JSON de metadatos.

    Campo clave para RAG:
      - descripcion: texto completo usado para vectorización semántica y TF-IDF.
      - url_catalogo: URL permanente para la generación de citas obligatorias.
    """
    id: str
    titulo: str
    descripcion: str
    url_catalogo: str
    anio: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("DocumentoPatrimonial requiere un ID único.")
        if not self.titulo:
            raise ValueError("DocumentoPatrimonial requiere un título.")

    @property
    def texto_indexable(self) -> str:
        """Concatenación título + descripción para vectorización e indexación."""
        return f"{self.titulo}. {self.descripcion}".strip()

    @property
    def tiene_url(self) -> bool:
        """Indica si el documento posee URL de catálogo para generar citas."""
        return bool(self.url_catalogo and self.url_catalogo.strip())
