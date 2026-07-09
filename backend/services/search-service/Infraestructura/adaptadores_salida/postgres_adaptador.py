"""
Adaptador de Salida — PostgreSQL (asyncpg)
==========================================
Implementación concreta de AtoMRepositoryPort que almacena y recupera
los metadatos Dublin Core del catálogo patrimonial UAH desde PostgreSQL.

Reemplaza al StaticJsonRepositoryAdapter en entornos de producción:
  - Elimina la carga de 6.5 MB de JSON en RAM en cada reinicio.
  - Permite busquedas exactas con indices B-tree y GIN sobre el texto.
  - Permite paginacion eficiente sobre el catalogo completo.
  - La fuente de verdad es la base de datos, no el sistema de archivos.

REGLA DE ORO: Este adaptador implementa la interfaz AtoMRepositoryPort
sin modificar ninguna linea del dominio. El GestorBusqueda, el Caso de
Uso y las entidades de dominio permanecen exactamente iguales.

Esquema SQL requerido (ejecutado por seed_database.py):
    CREATE TABLE documentos_patrimoniales (
        id           TEXT PRIMARY KEY,
        titulo       TEXT NOT NULL,
        descripcion  TEXT DEFAULT '',
        url_catalogo TEXT DEFAULT '',
        anio         TEXT,
        creator      TEXT,
        materias     TEXT,
        lugar        TEXT,
        categorias   TEXT,
        slug         TEXT
    );
"""

from __future__ import annotations

import asyncio
from typing import Optional

import asyncpg

from Dominio.puertos.repositorio_salida import AtoMRepositoryPort
from Dominio.entidades.documento_patrimonial import DocumentoPatrimonial


class PostgresRepositoryAdapter(AtoMRepositoryPort):
    """
    Adaptador de Salida concreto para PostgreSQL usando asyncpg.

    Implementa el contrato AtoMRepositoryPort con un pool de conexiones
    asincrono creado en el Composition Root (main.py lifespan).
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        """
        Args:
            pool: Pool de conexiones asyncpg creado en el lifespan de FastAPI.
        """
        self._pool = pool
        self._cache_todos: list[DocumentoPatrimonial] | None = None
        self._cache_por_id: dict[str, DocumentoPatrimonial] = {}
        self._vocabulario_creators: set[str] = set()

    # ------------------------------------------------------------------
    # Inicializacion — llamar una vez en el lifespan de FastAPI
    # ------------------------------------------------------------------

    async def cargar_cache(self) -> None:
        """
        Precarga el catalogo completo en memoria desde PostgreSQL.
        Debe llamarse UNA VEZ en el lifespan de FastAPI, antes de
        ensamblar el GestorBusqueda.
        """
        print("📦 [PostgresAdapter] Cargando catalogo desde PostgreSQL...")
        async with self._pool.acquire() as conn:
            filas = await conn.fetch(
                """
                SELECT id, titulo, descripcion, url_catalogo,
                       anio, creator, materias, lugar, categorias, slug
                FROM documentos_patrimoniales
                ORDER BY titulo
                """
            )

        documentos: list[DocumentoPatrimonial] = []
        indice: dict[str, DocumentoPatrimonial] = {}
        creators: set[str] = set()

        for fila in filas:
            try:
                doc = self._fila_a_entidad(fila)
            except ValueError:
                continue

            documentos.append(doc)
            indice[doc.id] = doc

            if fila["slug"]:
                indice[str(fila["slug"])] = doc

            if doc.creator:
                creators.add(doc.creator)

        self._cache_todos = documentos
        self._cache_por_id = indice
        self._vocabulario_creators = creators

        print(
            f"✅ [PostgresAdapter] {len(documentos)} documentos cargados "
            f"| {len(creators)} creators unicos registrados."
        )

    # ------------------------------------------------------------------
    # Implementacion del contrato AtoMRepositoryPort
    # ------------------------------------------------------------------

    async def obtener_todos(self) -> list[DocumentoPatrimonial]:
        """
        Retorna el catalogo completo desde la cache en memoria.
        No hace consultas a la BD en cada llamada.
        Async por contrato del puerto; devuelve datos de RAM sin suspender el event-loop.
        """
        if self._cache_todos is None:
            print("⚠️ [PostgresAdapter] obtener_todos() llamado antes de cargar_cache().")
            return []
        return self._cache_todos

    async def obtener_por_id(self, id_documento: str) -> Optional[DocumentoPatrimonial]:
        """
        Busca un documento por su ID o slug desde la cache en memoria (O(1)).
        Async por contrato del puerto; devuelve datos de RAM sin suspender el event-loop.
        """
        return self._cache_por_id.get(id_documento)

    async def obtener_por_id_async(self, id_documento: str) -> Optional[DocumentoPatrimonial]:
        """Version asincrona de obtener_por_id. Para llamadas fuera del dominio."""
        doc = self._cache_por_id.get(id_documento)
        if doc:
            return doc
        return await self._obtener_por_id_db(id_documento)

    # ------------------------------------------------------------------
    # Propiedad vocabulario_creators — compatibilidad con NLPExtractorAdapter
    # ------------------------------------------------------------------

    @property
    def vocabulario_creators(self) -> set[str]:
        """
        Conjunto de todos los dc:creator unicos del corpus.
        Usado por NLPExtractorAdapter para matching exacto de actores.
        """
        return self._vocabulario_creators

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    async def _obtener_por_id_db(self, id_documento: str) -> Optional[DocumentoPatrimonial]:
        """Consulta directa a PostgreSQL por ID o slug."""
        async with self._pool.acquire() as conn:
            fila = await conn.fetchrow(
                """
                SELECT id, titulo, descripcion, url_catalogo,
                       anio, creator, materias, lugar, categorias, slug
                FROM documentos_patrimoniales
                WHERE id = $1 OR slug = $1
                LIMIT 1
                """,
                id_documento,
            )
        if fila is None:
            return None
        try:
            return self._fila_a_entidad(fila)
        except ValueError:
            return None

    @staticmethod
    def _fila_a_entidad(fila: asyncpg.Record) -> DocumentoPatrimonial:
        """
        Mapea una fila asyncpg al tipo de dominio DocumentoPatrimonial.
        Anti-Corruption Layer: conocimiento del esquema SQL aislado aqui.
        """
        return DocumentoPatrimonial(
            id=str(fila["id"]),
            titulo=str(fila["titulo"]),
            descripcion=str(fila["descripcion"] or ""),
            url_catalogo=str(fila["url_catalogo"] or ""),
            anio=fila["anio"] or None,
            creator=fila["creator"] or None,
            materias=fila["materias"] or None,
            lugar=fila["lugar"] or None,
            categorias=fila["categorias"] or None,
        )
