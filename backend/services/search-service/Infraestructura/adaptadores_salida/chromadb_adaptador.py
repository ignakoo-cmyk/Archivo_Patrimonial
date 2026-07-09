"""
Adaptador de Salida — ChromaDB
================================
Implementa VectorStorePort utilizando la librería chromadb.

TODO el código "impuro" (dependiente de infraestructura de ChromaDB) se
concentra en este único archivo. Si mañana se migra a Pinecone o Weaviate,
SOLO este archivo cambia. El dominio y todos los demás adaptadores permanecen
intactos.

Mejoras v2:
- El texto enviado a ChromaDB para vectorización ahora incluye categorías,
  materias y año del documento (si están disponibles en el texto_indexable).
- Los metadatos almacenados se enriquecen con anio para posibilitar
  filtros temporales en futuras versiones.
"""

from __future__ import annotations

import os
from typing import Optional

import chromadb

from Dominio.puertos.repositorio_salida import VectorStorePort
from Dominio.entidades.documento_patrimonial import DocumentoPatrimonial


class ChromaDBAdapter(VectorStorePort):
    """
    Adaptador de Salida concreto para ChromaDB.

    Implementa el contrato VectorStorePort conectándose a una instancia
    HTTP de ChromaDB. Traduce las entidades de dominio al formato de
    ChromaDB y viceversa (mapeo bidireccional).
    """

    NOMBRE_COLECCION = "uah_archive"

    def __init__(self, host: str, puerto: int) -> None:
        """
        Establece la conexión con el servidor ChromaDB al inicializar.

        Args:
            host:   Hostname del servidor ChromaDB (ej. 'chromadb' en Docker).
            puerto: Puerto del servidor ChromaDB (ej. 8000).
        """
        try:
            self._cliente = chromadb.HttpClient(host=host, port=puerto)
            self._coleccion = self._cliente.get_or_create_collection(
                name=self.NOMBRE_COLECCION,
                metadata={"hnsw:space": "cosine"},
            )
            print(f"✅ [ChromaDBAdapter] Conectado a ChromaDB en {host}:{puerto}.")
        except Exception as error:
            print(f"⚠️ [ChromaDBAdapter] No se pudo conectar a ChromaDB: {error}")
            self._cliente = None
            self._coleccion = None

    # ──────────────────────────────────────────────────────────
    # Implementación del contrato VectorStorePort
    # ──────────────────────────────────────────────────────────

    def buscar_similares(
        self,
        consulta: str,
        n_resultados: int = 10,
        filtros: dict[str, str] = None,
    ) -> list[DocumentoPatrimonial]:
        """
        Delega la búsqueda vectorial a ChromaDB y mapea los resultados
        al tipo de dominio DocumentoPatrimonial. Acepta filtros exactos.

        NOTA: Para el flujo de búsqueda híbrida con PostgreSQL, preferir
        buscar_ids_similares() que retorna IDs para lookup completo en BD.
        """
        if not self._coleccion:
            return []

        where_clause = self._construir_where(filtros)

        try:
            resultado_crudo = self._coleccion.query(
                query_texts=[consulta],
                n_results=n_resultados,
                where=where_clause,
            )
        except Exception as error:
            print(f"❌ [ChromaDBAdapter] Error en búsqueda semántica: {error}")
            return []

        return self._mapear_resultados_a_entidades(resultado_crudo)

    def buscar_ids_similares(
        self,
        consulta: str,
        n_resultados: int = 10,
        filtros: dict[str, str] = None,
    ) -> list[str]:
        """
        Retorna únicamente los IDs de los documentos más similares en ChromaDB.

        Implementación del flujo híbrido real:
          ChromaDB → IDs → Repositorio (PostgreSQL/JSON) → DocumentoPatrimonial completo.

        Permite que la fuente de verdad de metadatos sea siempre el repositorio
        principal (PostgreSQL en producción, JSON en desarrollo), evitando
        inconsistencias entre lo indexado en Chroma y lo almacenado en la BD.
        """
        if not self._coleccion:
            return []

        where_clause = self._construir_where(filtros)

        try:
            resultado_crudo = self._coleccion.query(
                query_texts=[consulta],
                n_results=n_resultados,
                where=where_clause,
                include=[],  # Solo necesitamos los IDs, sin textos ni metadatos
            )
        except Exception as error:
            print(f"❌ [ChromaDBAdapter] Error en buscar_ids_similares: {error}")
            return []

        if not resultado_crudo.get("ids") or not resultado_crudo["ids"][0]:
            return []

        return resultado_crudo["ids"][0]

    def indexar_documentos(self, documentos: list[DocumentoPatrimonial]) -> None:
        """
        Convierte entidades de dominio al formato ChromaDB y ejecuta upsert
        en lotes para no saturar el servidor.

        Mejora v2: el texto de vectorización ahora incluye el texto_indexable
        completo de la entidad de dominio, que fue enriquecido previamente
        por el StaticJsonRepositoryAdapter con categorías, año y materias.
        """
        if not self._coleccion or not documentos:
            return

        lote_ids: list[str] = []
        lote_textos: list[str] = []
        lote_metadatos: list[dict] = []

        for doc in documentos:
            texto = doc.texto_indexable
            if not texto.strip():
                continue
            lote_ids.append(doc.id)
            lote_textos.append(texto)
            # Metadatos enriquecidos — permiten filtros en ChromaDB
            # (El tipo debe ser str, int, float, o bool para ChromaDB metadata)
            meta = {
                "titulo": doc.titulo,
                "url": doc.url_catalogo,
                "anio": doc.anio or "",
            }
            if doc.creator:
                meta["creator"] = doc.creator
            if doc.categorias:
                meta["categorias"] = doc.categorias
            if doc.materias:
                meta["materias"] = doc.materias
            if doc.lugar:
                meta["lugar"] = doc.lugar
            lote_metadatos.append(meta)

        tamanio_lote = 200
        total = 0
        for inicio in range(0, len(lote_ids), tamanio_lote):
            fin = inicio + tamanio_lote
            try:
                self._coleccion.upsert(
                    ids=lote_ids[inicio:fin],
                    documents=lote_textos[inicio:fin],
                    metadatas=lote_metadatos[inicio:fin],
                )
                total += len(lote_ids[inicio:fin])
            except Exception as error:
                print(f"⚠️ [ChromaDBAdapter] Error en lote {inicio}: {error}")

        print(f"✅ [ChromaDBAdapter] {total} documentos indexados en ChromaDB.")

    # ──────────────────────────────────────────────────────────
    # Mapeo privado: ChromaDB → Dominio
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _construir_where(filtros: dict[str, str] | None) -> dict | None:
        """
        Construye la cláusula 'where' de ChromaDB a partir de un diccionario
        de filtros clave-valor. Maneja el caso de filtro único y múltiple.
        """
        if not filtros:
            return None
        if len(filtros) == 1:
            k, v = list(filtros.items())[0]
            return {k: v}
        return {"$and": [{k: v} for k, v in filtros.items()]}

    @staticmethod
    def _mapear_resultados_a_entidades(resultado_chroma: dict) -> list[DocumentoPatrimonial]:
        """
        Traduce la estructura cruda de ChromaDB al tipo de dominio.
        Método privado de conocimiento local del adaptador.

        NOTA: Los DocumentoPatrimonial retornados aquí tendrán 'descripcion' vacía
        porque ChromaDB no almacena el texto completo. En el flujo híbrido con
        PostgreSQL, usar buscar_ids_similares() en su lugar para obtener los
        documentos completos desde la base de datos de metadatos.
        """
        if not resultado_chroma.get("ids") or not resultado_chroma["ids"][0]:
            return []

        entidades: list[DocumentoPatrimonial] = []
        ids = resultado_chroma["ids"][0]
        metadatos = resultado_chroma.get("metadatas", [[]])[0]

        for i, id_doc in enumerate(ids):
            meta = metadatos[i] if i < len(metadatos) else {}
            try:
                entidades.append(
                    DocumentoPatrimonial(
                        id=id_doc,
                        titulo=meta.get("titulo", "Sin título"),
                        descripcion="",          # ChromaDB no devuelve el texto completo
                        url_catalogo=meta.get("url", ""),
                        anio=meta.get("anio") or None,
                    )
                )
            except ValueError:
                # Si la entidad no cumple invariantes, se omite silenciosamente
                continue

        return entidades
