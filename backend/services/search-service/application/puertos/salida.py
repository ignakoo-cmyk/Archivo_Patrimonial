"""
Puertos de Salida (Outbound / Driven Ports)
============================================
Contratos abstractos que definen TODO lo que el Dominio necesita
del mundo exterior. Cada interfaz aquí representa una "promesa"
que algún adaptador de infraestructura DEBE cumplir.

Clasificación:
- VectorStorePort    → abstrae el motor de búsqueda semántica (ej. ChromaDB).
- LexicalSearchPort  → abstrae el índice léxico estadístico (ej. TF-IDF).
- AtoMRepositoryPort → abstrae el repositorio maestro de documentos.

REGLA DE ORO: Solo Python estándar. Sin imports de chromadb,
scikit-learn ni ninguna librería concreta.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from domain.search_context.models import DocumentoPatrimonial


class VectorStorePort(ABC):
    """
    Puerto de Salida — Almacén Vectorial.

    Define el contrato para la búsqueda semántica por embeddings.
    El dominio llama a este puerto sin saber si usa ChromaDB, Pinecone u otro.

    Implementado por:
    - ChromaDBAdapter     → adaptador de producción.
    - InMemoryVectorAdapter → adaptador ligero para pruebas unitarias.
    """

    @abstractmethod
    def buscar_similares(
        self,
        consulta: str,
        n_resultados: int = 10,
    ) -> list[DocumentoPatrimonial]:
        """
        Busca documentos semánticamente similares al texto de consulta.

        Args:
            consulta:     Texto en lenguaje natural a comparar semánticamente.
            n_resultados: Máximo de resultados a devolver.

        Returns:
            Lista de DocumentoPatrimonial ordenados por similitud descendente.
        """
        ...

    @abstractmethod
    def indexar_documentos(self, documentos: list[DocumentoPatrimonial]) -> None:
        """
        Indexa un listado de documentos en el almacén vectorial.
        Genera y persiste los embeddings correspondientes.

        Args:
            documentos: Entidades de dominio a indexar.
        """
        ...


class LexicalSearchPort(ABC):
    """
    Puerto de Salida — Índice de Búsqueda Léxica.

    Define el contrato para la búsqueda por relevancia estadística (TF-IDF).
    El dominio llama a este puerto sin saber si usa scikit-learn, BM25 u otro.

    Implementado por:
    - TFIDFAdapter          → adaptador de producción (scikit-learn).
    - MockLexicalAdapter    → adaptador para pruebas unitarias.
    """

    @abstractmethod
    def construir_indice(self, documentos: list[DocumentoPatrimonial]) -> None:
        """
        Construye el índice léxico en memoria a partir de una colección
        de documentos del dominio. Debe llamarse una vez al iniciar el servicio.
        """
        ...

    @abstractmethod
    def buscar_por_terminos(
        self,
        consulta: str,
        n_resultados: int = 10,
        umbral_minimo: float = 0.05,
    ) -> list[DocumentoPatrimonial]:
        """
        Realiza una búsqueda léxica usando ponderación de términos (TF-IDF).

        Args:
            consulta:       Texto de la búsqueda.
            n_resultados:   Máximo de resultados a devolver.
            umbral_minimo:  Puntuación mínima de similitud para incluir un resultado.

        Returns:
            Lista de DocumentoPatrimonial ordenados por similitud léxica.
        """
        ...


class AtoMRepositoryPort(ABC):
    """
    Puerto de Salida — Repositorio Maestro de Documentos.

    Define el contrato para acceder a la fuente de verdad del archivo patrimonial.
    Abstracciones que permiten cambiar la fuente de datos sin tocar el dominio.

    Implementado por:
    - JsonRepositorioAdapter  → lee del archivo JSON local (desarrollo/actual).
    - AtoMHttpAdapter         → consulta la API REST de AtoM (producción futura).
    """

    @abstractmethod
    def obtener_todos(self) -> list[DocumentoPatrimonial]:
        """
        Retorna el catálogo completo de documentos patrimoniales.
        Usado para construir el índice TF-IDF y las búsquedas exactas.
        """
        ...

    @abstractmethod
    def obtener_por_id(self, id_documento: str) -> Optional[DocumentoPatrimonial]:
        """
        Busca un documento por su ID único o código de referencia archivístico.

        Args:
            id_documento: ID interno o slug del documento en el catálogo.

        Returns:
            La entidad DocumentoPatrimonial si existe, None si no se encuentra.
        """
        ...
