"""
Search Context — Puertos de Salida (Outbound Ports)
=====================================================
Contratos abstractos que definen lo que el Search Context necesita
del mundo exterior. Cada interfaz representa una "promesa" que un
adaptador de infraestructura concreta debe cumplir.

REGLA DE ORO: Solo Python estándar. Sin chromadb, scikit-learn ni httpx.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from domain.search_context.models import DocumentoPatrimonial


class VectorStorePort(ABC):
    """Puerto para búsqueda semántica por embeddings. Implementado por ChromaDBAdapter."""

    @abstractmethod
    def buscar_similares(self, consulta: str, n_resultados: int = 10) -> list[DocumentoPatrimonial]:
        """Retorna documentos semánticamente similares al texto de consulta."""
        ...

    @abstractmethod
    def indexar_documentos(self, documentos: list[DocumentoPatrimonial]) -> None:
        """Genera y persiste embeddings para una colección de documentos."""
        ...


class LexicalSearchPort(ABC):
    """Puerto para búsqueda léxica estadística. Implementado por TFIDFAdapter."""

    @abstractmethod
    def construir_indice(self, documentos: list[DocumentoPatrimonial]) -> None:
        """Construye el índice en memoria. Debe llamarse una vez al inicio."""
        ...

    @abstractmethod
    def buscar_por_terminos(
        self, consulta: str, n_resultados: int = 10, umbral_minimo: float = 0.05
    ) -> list[DocumentoPatrimonial]:
        """Retorna documentos ordenados por similitud TF-IDF."""
        ...


class AtoMRepositoryPort(ABC):
    """Puerto para acceder al repositorio maestro de documentos. Implementado por JsonRepositorioAdapter."""

    @abstractmethod
    def obtener_todos(self) -> list[DocumentoPatrimonial]:
        """Retorna el catálogo completo de documentos patrimoniales."""
        ...

    @abstractmethod
    def obtener_por_id(self, id_documento: str) -> Optional[DocumentoPatrimonial]:
        """Retorna un documento por ID/slug, o None si no existe."""
        ...
