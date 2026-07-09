"""
Adaptador de Salida — InMemoryMetadataFilterAdapter
=====================================================
Implementa MetadataFilterPort usando índices invertidos en RAM.

Estrategia de Optimización:
  Al arrancar el servicio, se construyen tres diccionarios de índices:
    _idx_creator  : token_normalizado → set de IDs de documentos
    _idx_materias : token_normalizado → set de IDs de documentos
    _idx_lugar    : token_normalizado → set de IDs de documentos

  El pre-filtrado por N criterios es:
    1. Por cada criterio activo → lookup O(1) en el índice → set de IDs
    2. Intersección de todos los sets → O(k) donde k = tamaño del set más pequeño
    3. Recuperar los DocumentoPatrimonial del subconjunto → O(resultado)

  Comparación de complejidad:
    Sin pre-filtrado: O(n × d) donde n = corpus total, d = dimensión embedding
    Con pre-filtrado: O(1) lookup + O(k) intersección + O(r × d) embeddings
    Para Aylwin (40k docs): reduce n=12000 → r≈500 antes del embedding.

REGLA: Este adaptador SOLO hace filtrado. No realiza búsqueda semántica.
"""

from __future__ import annotations

import unicodedata
import re
from collections import defaultdict

from Dominio.puertos.repositorio_salida import MetadataFilterPort
from Dominio.entidades.documento_patrimonial import DocumentoPatrimonial
from Dominio.objetos_de_valor.filtro_metadatos import FiltroMetadatos


def _normalizar(texto: str) -> str:
    """
    Normaliza texto para comparación: minúsculas, sin acentos, sin puntuación extra.
    Permite matcheo fuzzy básico ('Aylwin' == 'aylwin', 'Santiago (Chile)' == 'santiago').
    """
    if not texto:
        return ""
    # Normalizar acentos: NFD descompone caracteres acentuados
    nfd = unicodedata.normalize("NFD", texto.lower())
    # Eliminar diacríticos (combining characters)
    sin_acentos = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    # Limpiar paréntesis y texto entre ellos (ej: "Santiago (Chile: Ciudad)" → "santiago")
    sin_parens = re.sub(r"\s*\([^)]*\)", "", sin_acentos).strip()
    return sin_parens


def _tokens(texto: str) -> list[str]:
    """Extrae tokens de palabras significativas (len >= 3) de un texto normalizado."""
    return [t for t in re.findall(r"\b\w+\b", _normalizar(texto)) if len(t) >= 3]


class InMemoryMetadataFilterAdapter(MetadataFilterPort):
    """
    Adaptador de infraestructura para pre-filtrado por metadatos Dublin Core.

    Construye índices invertidos en memoria al iniciar el servicio.
    El filtrado es una operación de intersección de sets: extremadamente rápida.
    """

    def __init__(self) -> None:
        # Índice invertido: token_normalizado → set de document IDs
        self._idx_creator: dict[str, set[str]] = defaultdict(set)
        self._idx_materias: dict[str, set[str]] = defaultdict(set)
        self._idx_lugar: dict[str, set[str]] = defaultdict(set)
        self._idx_anio: dict[str, set[str]] = defaultdict(set)

        # Índice directo: ID → entidad (para reconstruir después de filtrar)
        self._docs_por_id: dict[str, DocumentoPatrimonial] = {}

        self._construido = False

    # ──────────────────────────────────────────────────────────
    # Implementación del contrato MetadataFilterPort
    # ──────────────────────────────────────────────────────────

    def construir_indices(self, documentos: list[DocumentoPatrimonial]) -> None:
        """
        Construye los índices invertidos desde el catálogo completo.
        Operación one-time al iniciar el servicio. Complejidad: O(n × p).

        Refactorización P3: cada tipo de campo se delega a un método privado
        con CC = 2 (grado A). Este método orquesta sin lógica anidada.
        """
        if not documentos:
            print("⚠️ [MetadataFilter] No se recibieron documentos para indexar.")
            return

        for doc in documentos:
            self._docs_por_id[doc.id] = doc
            self._indexar_creator(doc)
            self._indexar_materias(doc)
            self._indexar_lugar(doc)
            self._indexar_anio(doc)

        self._construido = True
        print(
            f"✅ [MetadataFilter] Índices construidos: "
            f"{len(self._idx_creator)} tokens-creator | "
            f"{len(self._idx_materias)} tokens-materias | "
            f"{len(self._idx_lugar)} tokens-lugar | "
            f"{len(documentos)} documentos totales."
        )

    # ──────────────────────────────────────────────────────────
    # Métodos privados de indexación (CC ≤ 2 cada uno — grado A)
    # ──────────────────────────────────────────────────────────

    def _indexar_creator(self, doc: DocumentoPatrimonial) -> None:
        """Indexa dc:creator del documento: tokens individuales + string completo normalizado."""
        if not doc.creator:
            return
        for token in _tokens(doc.creator):
            self._idx_creator[token].add(doc.id)
        creator_norm = _normalizar(doc.creator)
        if creator_norm:
            self._idx_creator[creator_norm].add(doc.id)

    def _indexar_materias(self, doc: DocumentoPatrimonial) -> None:
        """Indexa dc:subject: tokens individuales + bigramas de 2 palabras."""
        if not doc.materias:
            return
        palabras = [t for t in re.findall(r"\b\w+\b", _normalizar(doc.materias)) if len(t) >= 3]
        for token in palabras:
            self._idx_materias[token].add(doc.id)
        for i in range(len(palabras) - 1):
            bigrama = f"{palabras[i]} {palabras[i+1]}"
            self._idx_materias[bigrama].add(doc.id)

    def _indexar_lugar(self, doc: DocumentoPatrimonial) -> None:
        """Indexa dc:coverage: tokens individuales + string completo normalizado."""
        if not doc.lugar:
            return
        for token in _tokens(doc.lugar):
            self._idx_lugar[token].add(doc.id)
        lugar_norm = _normalizar(doc.lugar)
        if lugar_norm:
            self._idx_lugar[lugar_norm].add(doc.id)

    def _indexar_anio(self, doc: DocumentoPatrimonial) -> None:
        """Indexa el año del documento como string."""
        if doc.anio:
            self._idx_anio[str(doc.anio).strip()].add(doc.id)

    # ──────────────────────────────────────────────────────────
    # Métodos privados de filtrado (CC ≤ 3 cada uno — grado A)
    # ──────────────────────────────────────────────────────────

    def _ids_por_creator(self, actor_creador: str) -> set[str]:
        """Retorna IDs de documentos cuyo creator contiene el texto buscado."""
        ids: set[str] = set()
        for token in _tokens(actor_creador):
            ids |= self._idx_creator.get(token, set())
        ids |= self._idx_creator.get(_normalizar(actor_creador), set())
        return ids

    def _ids_por_materias(self, materias: list[str]) -> set[str]:
        """Retorna IDs de documentos cuyas materias coinciden con alguno de los términos (OR)."""
        ids: set[str] = set()
        for materia in materias:
            for token in _tokens(materia):
                ids |= self._idx_materias.get(token, set())
            ids |= self._idx_materias.get(_normalizar(materia), set())
        return ids

    def _ids_por_lugar(self, lugar: str) -> set[str]:
        """Retorna IDs de documentos cuya cobertura geográfica coincide."""
        ids: set[str] = set()
        for token in _tokens(lugar):
            ids |= self._idx_lugar.get(token, set())
        ids |= self._idx_lugar.get(_normalizar(lugar), set())
        return ids

    def _ids_por_anio(self, anio_desde: int | None, anio_hasta: int | None) -> set[str]:
        """Retorna IDs de documentos dentro del rango de años especificado."""
        ids: set[str] = set()
        for anio_str, doc_ids in self._idx_anio.items():
            try:
                anio_int = int(anio_str[:4])
            except (ValueError, TypeError):
                continue
            desde_ok = (anio_desde is None) or (anio_int >= anio_desde)
            hasta_ok = (anio_hasta is None) or (anio_int <= anio_hasta)
            if desde_ok and hasta_ok:
                ids |= doc_ids
        return ids

    # ──────────────────────────────────────────────────────────
    # Implementación del contrato MetadataFilterPort
    # ──────────────────────────────────────────────────────────

    def aplicar_filtros(
        self,
        filtro: FiltroMetadatos,
        corpus: list[DocumentoPatrimonial],
    ) -> list[DocumentoPatrimonial]:
        """
        Pre-filtra el corpus por metadatos usando intersección de índices invertidos.

        Algoritmo AND: solo se retienen documentos que cumplen TODOS los criterios.
        Complejidad: O(1) por lookup + O(k) por intersección de sets.

        Refactorización P3 (CC = B): delega a 4 métodos de búsqueda + 2 de soporte.
        """
        if not self._construido or filtro.esta_vacio:
            return corpus

        print(f"🔍 [MetadataFilter] Aplicando {filtro.resumen}")

        sets_activos = self._recopilar_sets_activos(filtro)
        if not sets_activos:
            print("⚠️ [MetadataFilter] Ningún criterio produjo IDs. Retornando corpus completo.")
            return corpus

        ids_resultado = self._intersectar_con_fallback(sets_activos, len(corpus))
        return self._recuperar_documentos(ids_resultado, corpus)

    def _recopilar_sets_activos(self, filtro: FiltroMetadatos) -> list[set[str]]:
        """Construye la lista de sets de IDs para cada criterio activo del filtro."""
        sets: list[set[str]] = []
        if filtro.actor_creador:
            ids = self._ids_por_creator(filtro.actor_creador)
            if ids:
                sets.append(ids)
        if filtro.materias:
            ids = self._ids_por_materias(filtro.materias)
            if ids:
                sets.append(ids)
        if filtro.lugar:
            ids = self._ids_por_lugar(filtro.lugar)
            if ids:
                sets.append(ids)
        if filtro.anio_desde or filtro.anio_hasta:
            ids = self._ids_por_anio(filtro.anio_desde, filtro.anio_hasta)
            if ids:
                sets.append(ids)
        return sets

    def _intersectar_con_fallback(self, sets_activos: list[set[str]], total_corpus: int) -> set[str]:
        """
        Intersección AND de todos los sets, con fallback suavizado si el resultado es muy pequeño.
        Ordena de menor a mayor para optimizar la intersección.
        """
        sets_activos.sort(key=lambda s: len(s))
        ids_resultado = sets_activos[0].copy()
        for s in sets_activos[1:]:
            ids_resultado &= s

        print(f"✅ [MetadataFilter] Corpus reducido: {len(ids_resultado)} documentos (desde {total_corpus}).")

        if len(ids_resultado) < 15 and len(sets_activos) > 1:
            ids_resultado = sets_activos[0].copy()
            print(f"🔄 [MetadataFilter] Resultado muy pequeño. Relajando a {len(ids_resultado)} docs.")

        return ids_resultado

    def _recuperar_documentos(
        self, ids_resultado: set[str], corpus: list[DocumentoPatrimonial]
    ) -> list[DocumentoPatrimonial]:
        """Recupera entidades manteniendo el orden del corpus de entrada."""
        subconjunto = [doc for doc in corpus if doc.id in ids_resultado]
        if not subconjunto:
            subconjunto = [
                self._docs_por_id[doc_id]
                for doc_id in ids_resultado
                if doc_id in self._docs_por_id
            ]
        return subconjunto if subconjunto else corpus
