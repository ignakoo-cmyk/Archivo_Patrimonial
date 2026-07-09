"""
Search Context — Entidad de Dominio: DocumentoPatrimonial
==========================================================
Entidad raíz de agregado del Search Context.
Representa un registro archivístico del Archivo Patrimonial UAH,
mapeado desde el esquema Dublin Core de AtoM o el JSON de metadatos.

REGLA DE ORO: Sin imports de FastAPI, ChromaDB, scikit-learn ni ningún framework.
Solo Python estándar. Estas clases son el lenguaje ubicuo del dominio de búsqueda.

v3 — Campos Dublin Core completos:
  - creator:  dc:creator  (autor / actor / entidad creadora)
  - materias: dc:subject  (palabras clave temáticas del tesauro)
  - lugar:    dc:coverage (cobertura geográfica)
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

    Campos Dublin Core (v3):
      - creator:   dc:creator  — quién creó el documento (persona/institución).
      - materias:  dc:subject  — lista de temas/descriptores del tesauro archivístico.
      - lugar:     dc:coverage — cobertura geográfica del documento.
      - categorias: clasificación del árbol de fondos.
    """
    id: str
    titulo: str
    descripcion: str
    url_catalogo: str
    anio: Optional[str] = None
    materias: Optional[str] = None     # dc:subject — palabras clave temáticas
    categorias: Optional[str] = None   # categorías del árbol de clasificación
    creator: Optional[str] = None      # dc:creator — actor/autor principal
    lugar: Optional[str] = None        # dc:coverage — cobertura geográfica

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("DocumentoPatrimonial requiere un ID único.")
        if not self.titulo:
            raise ValueError("DocumentoPatrimonial requiere un título.")

    @property
    def texto_indexable(self) -> str:
        """
        Concatenación enriquecida de campos semánticos para vectorización.
        Incluye título, creator, descripción, materias, categorías y lugar cuando disponibles.
        El orden replica la importancia semántica: el título tiene más peso
        porque aparece primero en el embedding. El creator también se pondera
        alto porque ancla la identidad archivística del documento.
        """
        partes = [self.titulo]
        if self.creator:
            partes.append(self.creator)
        if self.descripcion:
            partes.append(self.descripcion)
        if self.materias:
            partes.append(self.materias)
        if self.categorias:
            partes.append(self.categorias)
        if self.lugar:
            partes.append(self.lugar)
        if self.anio:
            partes.append(self.anio)
        return ". ".join(p.strip() for p in partes if p.strip())

    @property
    def tiene_url(self) -> bool:
        """Indica si el documento posee URL de catálogo para generar citas."""
        return bool(self.url_catalogo and self.url_catalogo.strip())

