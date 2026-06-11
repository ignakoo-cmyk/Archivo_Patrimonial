"""
Search Context — Modelos de Dominio
=====================================
Entidades y Objetos de Valor del Bounded Context de Recuperación de Información.

REGLA DE ORO: Sin imports de FastAPI, ChromaDB, scikit-learn ni ningún framework.
Solo Python estándar. Estas clases son el lenguaje ubicuo del dominio de búsqueda.

Lenguaje Ubicuo de este contexto:
  - Consulta:              intención del usuario en lenguaje natural.
  - DocumentoPatrimonial:  registro del acervo histórico de la UAH.
  - ResultadoBusqueda:     documento fusionado con su puntuación RRF.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────────
# OBJETOS DE VALOR — Inmutables por diseño (frozen=True)
# ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Consulta:
    """
    Objeto de Valor que encapsula una búsqueda del usuario.
    Inmutable: una vez creada, sus atributos no cambian.
    Valida sus propias invariantes de dominio en la construcción.
    """
    texto: str
    limite: int = 5

    def __post_init__(self) -> None:
        if not self.texto or not self.texto.strip():
            raise ValueError("La consulta no puede estar vacía.")
        if not (1 <= self.limite <= 50):
            raise ValueError(
                f"El límite debe estar entre 1 y 50. Recibido: {self.limite}"
            )

    @property
    def texto_normalizado(self) -> str:
        """Texto en minúsculas y sin espacios extremos para comparaciones."""
        return self.texto.strip().lower()


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


@dataclass(frozen=True)
class ResultadoBusqueda:
    """
    Objeto de Valor que encapsula el producto final del algoritmo RRF.
    Agrupa un documento con su puntuación de relevancia compuesta.
    """
    documento: DocumentoPatrimonial
    puntuacion_rrf: float

    def __post_init__(self) -> None:
        if self.puntuacion_rrf < 0:
            raise ValueError("La puntuación RRF no puede ser negativa.")
