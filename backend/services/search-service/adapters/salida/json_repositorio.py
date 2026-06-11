"""
Adaptador de Salida — Repositorio JSON Local
=============================================
Implementa AtoMRepositoryPort leyendo del archivo JSON de metadatos exportado
(clean_with_metadata.json). Este es el adaptador actual de producción mientras
no se tenga acceso directo a la API de AtoM.

Responsabilidades:
- Cargar el catálogo completo desde el archivo JSON al iniciar.
- Mapear cada entrada del JSON al tipo de dominio DocumentoPatrimonial.
- Proveer búsqueda por ID o slug.

Si en el futuro se activa la integración real con AtoM, se crea un nuevo
AtoMHttpRepositorioAdapter y se sustituye en main.py. Este archivo queda intacto.
"""

from __future__ import annotations

import json
import os
from typing import Optional

from application.puertos.salida import AtoMRepositoryPort
from domain.search_context.models import DocumentoPatrimonial


class JsonRepositorioAdapter(AtoMRepositoryPort):
    """
    Adaptador de Salida concreto que lee los documentos patrimoniales
    desde un archivo JSON local.

    Carga todos los documentos en memoria al inicializar (estrategia eager)
    para maximizar la velocidad de las búsquedas exactas y construcción del TF-IDF.
    """

    def __init__(self, ruta_archivo: str = "data/clean_with_metadata.json") -> None:
        """
        Args:
            ruta_archivo: Ruta relativa o absoluta al archivo JSON de metadatos.
        """
        self._ruta_archivo = ruta_archivo
        self._documentos: list[DocumentoPatrimonial] = []
        self._indice_por_id: dict[str, DocumentoPatrimonial] = {}
        self._cargar_documentos()

    # ──────────────────────────────────────────────────────────
    # Implementación del contrato AtoMRepositoryPort
    # ──────────────────────────────────────────────────────────

    def obtener_todos(self) -> list[DocumentoPatrimonial]:
        """Retorna el catálogo completo cargado en memoria."""
        return self._documentos

    def obtener_por_id(self, id_documento: str) -> Optional[DocumentoPatrimonial]:
        """
        Búsqueda por ID o slug usando el índice en memoria (O(1)).

        Args:
            id_documento: ID numérico (como string) o slug del documento.

        Returns:
            DocumentoPatrimonial si existe, None si no se encontró.
        """
        return self._indice_por_id.get(id_documento)

    # ──────────────────────────────────────────────────────────
    # Métodos privados de infraestructura
    # ──────────────────────────────────────────────────────────

    def _cargar_documentos(self) -> None:
        """
        Carga el archivo JSON y construye la lista de entidades y el índice.
        Ignora entradas inválidas sin detener la carga completa.
        """
        if not os.path.exists(self._ruta_archivo):
            print(
                f"⚠️ [JsonRepositorioAdapter] Archivo no encontrado: {self._ruta_archivo}"
            )
            return

        try:
            with open(self._ruta_archivo, "r", encoding="utf-8", errors="ignore") as f:
                datos_crudos: list[dict] = json.load(f)
        except Exception as error:
            print(f"❌ [JsonRepositorioAdapter] Error leyendo JSON: {error}")
            return

        omitidos = 0
        for idx, entrada in enumerate(datos_crudos):
            documento = self._mapear_entrada_a_entidad(entrada, idx)
            if documento is None:
                omitidos += 1
                continue
            self._documentos.append(documento)
            # Indexar por id y por slug para recuperación O(1)
            self._indice_por_id[documento.id] = documento
            slug = entrada.get("slug")
            if slug and slug != documento.id:
                self._indice_por_id[str(slug)] = documento

        print(
            f"✅ [JsonRepositorioAdapter] {len(self._documentos)} documentos cargados "
            f"({omitidos} omitidos) desde '{self._ruta_archivo}'."
        )

    @staticmethod
    def _mapear_entrada_a_entidad(entrada: dict, idx: int) -> Optional[DocumentoPatrimonial]:
        """
        Traduce una entrada del JSON crudo al tipo de dominio DocumentoPatrimonial.
        Retorna None si la entrada no cumple los requisitos mínimos del dominio.
        """
        # Determinar ID: preferir campo 'id', fallback a 'slug' o al índice de la lista
        id_raw = entrada.get("id") or entrada.get("slug")
        if not id_raw:
            id_raw = str(idx)

        titulo = entrada.get("title", "").strip()
        if not titulo:
            return None

        try:
            return DocumentoPatrimonial(
                id=str(id_raw),
                titulo=titulo,
                descripcion=entrada.get("description", ""),
                url_catalogo=entrada.get("href", ""),
                anio=entrada.get("year") or entrada.get("date"),
            )
        except ValueError:
            # Falla de invariante del dominio — se omite silenciosamente
            return None
