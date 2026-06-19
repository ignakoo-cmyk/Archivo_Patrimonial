"""
Adaptador de Salida — ChromaDB
================================
Implementa VectorStorePort utilizando la librería chromadb.

TODO el código "impuro" (dependiente de infraestructura de ChromaDB) se
concentra en este único archivo. Si mañana se migra a Pinecone o Weaviate,
SOLO este archivo cambia. El dominio y todos los demás adaptadores permanecen
intactos.
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
    ) -> list[DocumentoPatrimonial]:
        """
        Delega la búsqueda vectorial a ChromaDB y mapea los resultados
        al tipo de dominio DocumentoPatrimonial.
        """
        if not self._coleccion:
            return []

        try:
            resultado_crudo = self._coleccion.query(
                query_texts=[consulta],
                n_results=n_resultados,
            )
        except Exception as error:
            # Política de resiliencia: falla silenciosa para no bloquear el RRF
            print(f"❌ [ChromaDBAdapter] Error en búsqueda semántica: {error}")
            return []

        return self._mapear_resultados_a_entidades(resultado_crudo)

    def indexar_documentos(self, documentos: list[DocumentoPatrimonial]) -> None:
        """
        Convierte entidades de dominio al formato ChromaDB y ejecuta upsert
        en lotes para no saturar el servidor.
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
            lote_metadatos.append({
                "titulo": doc.titulo,
                "url": doc.url_catalogo,
            })

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
    def _mapear_resultados_a_entidades(resultado_chroma: dict) -> list[DocumentoPatrimonial]:
        """
        Traduce la estructura cruda de ChromaDB al tipo de dominio.
        Método privado de conocimiento local del adaptador.
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
                    )
                )
            except ValueError:
                # Si la entidad no cumple invariantes, se omite silenciosamente
                continue

        return entidades
