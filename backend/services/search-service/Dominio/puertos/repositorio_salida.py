"""
Search Context — Puertos de Salida (Outbound / Driven Ports)
==============================================================
Contratos abstractos que definen TODO lo que el Dominio necesita
del mundo exterior. Cada interfaz aquí representa una "promesa"
que algún adaptador de infraestructura DEBE cumplir.

Clasificación:
- VectorStorePort    → abstrae el motor de búsqueda semántica (ej. ChromaDB).
- LexicalSearchPort  → abstrae el índice léxico estadístico (ej. TF-IDF).
- AtoMRepositoryPort → abstrae el repositorio maestro de documentos.
- MetadataFilterPort → abstrae el motor de pre-filtrado por metadatos Dublin Core.

REGLA DE ORO: Solo Python estándar. Sin imports de chromadb,
scikit-learn ni ninguna librería concreta.

Modelo de concurrencia:
Todos los métodos de AtoMRepositoryPort son async para ser compatibles
con el modelo ASGI de FastAPI. Los adaptadores basados en memoria
(JSON) devuelven datos cargados en __init__ de forma inmediata;
los adaptadores remotos (HTTP/AtoM API) harán I/O de red real con await.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

# Python 3.12: corrutinas nativas. Todos los puertos de repositorio
# declaran métodos async para que el Dominio sea agnóstico al
# origen de datos (en memoria, HTTP, base de datos).
import asyncio  # noqa: F401 — importado para que el linter reconozca el contexto async

from Dominio.entidades.documento_patrimonial import DocumentoPatrimonial
from Dominio.objetos_de_valor.filtro_metadatos import FiltroMetadatos


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
        filtros: dict[str, str] = None,
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
    def buscar_ids_similares(
        self,
        consulta: str,
        n_resultados: int = 10,
        filtros: dict[str, str] = None,
    ) -> list[str]:
        """
        Retorna únicamente los IDs de los documentos más similares semánticamente.

        Diseñado para la búsqueda híbrida real:
          ChromaDB → IDs → PostgreSQL/Repositorio → DocumentoPatrimonial completo.

        Esto evita depender de los metadatos almacenados en Chroma (que están
        incompletos, p.ej. sin 'descripcion'), y permite que la fuente de verdad
        sea siempre la base de datos de metadatos.

        Args:
            consulta:     Texto en lenguaje natural a comparar semánticamente.
            n_resultados: Máximo de IDs a devolver.
            filtros:      Filtros de metadatos opcionales (ChromaDB where clause).

        Returns:
            Lista de IDs de documento ordenados por similitud descendente.
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
            umbral_minimo:  Puntuación mínima de similitud para incluir resultado.

        Returns:
            Lista de DocumentoPatrimonial ordenados por similitud léxica.
        """
        ...


class AtoMRepositoryPort(ABC):
    """
    Puerto de Salida — Repositorio Maestro de Documentos.

    Define el contrato para acceder a la fuente de verdad del archivo patrimonial.
    Los métodos son async para ser agnósticos al origen de datos:
      - Adaptadores en memoria (JSON) retornan datos ya cargados.
      - Adaptadores remotos (HTTP, DB) realizan I/O de red con await.

    Implementado actualmente por:
    - StaticJsonRepositoryAdapter → lee del JSON local (Infraestructura/datos/).

    # ── PUNTO DE EXTENSIÓN: AtomApiAdapter (producción futura) ────────────────
    #
    # Para conectar la API REST de AtoM sin modificar Dominio ni Aplicación:
    #
    #   1. Crear en Infraestructura/adaptadores_salida/atom_api_adaptador.py:
    #
    #        class AtomApiAdapter(AtoMRepositoryPort):
    #            def __init__(self, base_url: str, api_key: str, cliente_http: httpx.AsyncClient):
    #                ...
    #
    #            async def obtener_todos(self) -> list[DocumentoPatrimonial]:
    #                response = await self._cliente.get(f"{self._base_url}/api/informationobjects")
    #                return [self._mapear(item) for item in response.json()["results"]]
    #
    #            async def obtener_por_id(self, id_documento: str) -> Optional[DocumentoPatrimonial]:
    #                response = await self._cliente.get(f"{self._base_url}/api/informationobjects/{id_documento}")
    #                return self._mapear(response.json()) if response.status_code == 200 else None
    #
    #   2. En main.py (Composition Root), instanciar y pasar al GestorBusqueda:
    #
    #        atom_cliente = httpx.AsyncClient()
    #        repositorio = AtomApiAdapter(
    #            base_url=os.getenv("ATOM_BASE_URL"),
    #            api_key=os.getenv("ATOM_API_KEY"),
    #            cliente_http=atom_cliente,
    #        )
    #
    # RESULTADO: Dominio, Aplicación y todos los demás adaptadores quedan intactos.
    # ─────────────────────────────────────────────────────────────────────────────
    """

    @abstractmethod
    async def obtener_todos(self) -> list[DocumentoPatrimonial]:
        """
        Retorna el catálogo completo de documentos patrimoniales.
        Usado para construir el índice TF-IDF y las búsquedas exactas.
        """
        ...

    @abstractmethod
    async def obtener_por_id(self, id_documento: str) -> Optional[DocumentoPatrimonial]:
        """
        Busca un documento por su ID único o código de referencia archivístico.

        Args:
            id_documento: ID interno o slug del documento en el catálogo.

        Returns:
            La entidad DocumentoPatrimonial si existe, None si no se encuentra.
        """
        ...


class MetadataFilterPort(ABC):
    """
    Puerto de Salida — Motor de Pre-filtrado por Metadatos Dublin Core.

    Define el contrato para reducir drásticamente el espacio de búsqueda
    ANTES de calcular embeddings o TF-IDF. Es el primer paso en la
    búsqueda híbrida: filtrado exacto → embeddings sobre el subconjunto.

    Implementado por:
    - InMemoryMetadataFilterAdapter → índices invertidos en RAM (producción actual).

    Por qué importa:
    Si Patricio Aylwin tiene 40.000 documentos de 12.000 totales,
    buscar 'Aylwin + derechos humanos' sin pre-filtrar requiere
    calcular similitud coseno sobre los 12.000. Con pre-filtrado,
    primero se intersectan los sets del índice invertido (O(1) lookup,
    O(k) intersección) y luego solo se vectoriza el subconjunto.
    """

    @abstractmethod
    def aplicar_filtros(
        self,
        filtro: FiltroMetadatos,
        corpus: list[DocumentoPatrimonial],
    ) -> list[DocumentoPatrimonial]:
        """
        Aplica los filtros de metadatos sobre un corpus y retorna
        los documentos que cumplen TODOS los criterios activos (AND lógico).

        Args:
            filtro:  FiltroMetadatos con los criterios extraídos del NLP.
            corpus:  Lista completa de documentos (o subconjunto ya acotado).

        Returns:
            Subconjunto de documentos que superan el filtro.
            Si el filtro está vacío, devuelve el corpus completo sin modificar.
        """
        ...

    @abstractmethod
    def construir_indices(self, documentos: list[DocumentoPatrimonial]) -> None:
        """
        Construye los índices invertidos en memoria.
        Debe llamarse UNA VEZ en el lifespan de la aplicación.

        Args:
            documentos: Catálogo completo de DocumentoPatrimonial.
        """
        ...
