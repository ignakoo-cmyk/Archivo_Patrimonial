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
        Construye los tres índices invertidos desde el catálogo completo.
        Operación one-time al iniciar el servicio. Complejidad: O(n × p)
        donde p = promedio de tokens por documento.
        """
        if not documentos:
            print("⚠️ [MetadataFilter] No se recibieron documentos para indexar.")
            return

        for doc in documentos:
            # Registro en el índice directo
            self._docs_por_id[doc.id] = doc

            # Indexar dc:creator (actor_creador)
            if doc.creator:
                for token in _tokens(doc.creator):
                    self._idx_creator[token].add(doc.id)
                # También indexar el string completo normalizado
                creator_norm = _normalizar(doc.creator)
                if creator_norm:
                    self._idx_creator[creator_norm].add(doc.id)

            # Indexar dc:subject (materias)
            if doc.materias:
                for token in _tokens(doc.materias):
                    self._idx_materias[token].add(doc.id)
                # También indexar frases compuestas de 2 palabras
                palabras = [t for t in re.findall(r"\b\w+\b", _normalizar(doc.materias)) if len(t) >= 3]
                for i in range(len(palabras) - 1):
                    bigrama = f"{palabras[i]} {palabras[i+1]}"
                    self._idx_materias[bigrama].add(doc.id)

            # Indexar dc:coverage (lugar)
            if doc.lugar:
                for token in _tokens(doc.lugar):
                    self._idx_lugar[token].add(doc.id)
                lugar_norm = _normalizar(doc.lugar)
                if lugar_norm:
                    self._idx_lugar[lugar_norm].add(doc.id)

            # Indexar año
            if doc.anio:
                self._idx_anio[str(doc.anio).strip()].add(doc.id)

        self._construido = True
        print(
            f"✅ [MetadataFilter] Índices construidos: "
            f"{len(self._idx_creator)} tokens-creator | "
            f"{len(self._idx_materias)} tokens-materias | "
            f"{len(self._idx_lugar)} tokens-lugar | "
            f"{len(documentos)} documentos totales."
        )

    def aplicar_filtros(
        self,
        filtro: FiltroMetadatos,
        corpus: list[DocumentoPatrimonial],
    ) -> list[DocumentoPatrimonial]:
        """
        Pre-filtra el corpus por metadatos usando intersección de índices invertidos.

        Algoritmo AND: solo se retienen documentos que cumplen TODOS los criterios.
        Complejidad: O(1) por lookup + O(k) por intersección de sets.

        Si el filtro está vacío, retorna el corpus completo sin modificar.
        Si el corpus filtrado es < 20 documentos, incluye un fallback suavizado.
        """
        if not self._construido:
            print("⚠️ [MetadataFilter] Índices no construidos. Retornando corpus completo.")
            return corpus

        if filtro.esta_vacio:
            return corpus

        print(f"🔍 [MetadataFilter] Aplicando {filtro.resumen}")

        # Conjuntos de IDs que satisfacen cada criterio
        sets_activos: list[set[str]] = []

        # ── Filtro por actor/creador ──────────────────────────────────────────
        if filtro.actor_creador:
            ids_creator: set[str] = set()
            for token in _tokens(filtro.actor_creador):
                ids_creator |= self._idx_creator.get(token, set())
            # También buscar el nombre completo normalizado
            nombre_norm = _normalizar(filtro.actor_creador)
            ids_creator |= self._idx_creator.get(nombre_norm, set())
            if ids_creator:
                sets_activos.append(ids_creator)

        # ── Filtro por materias (OR entre términos de la misma materia) ───────
        if filtro.materias:
            ids_materias: set[str] = set()
            for materia in filtro.materias:
                for token in _tokens(materia):
                    ids_materias |= self._idx_materias.get(token, set())
                # Buscar bigrama completo también
                materia_norm = _normalizar(materia)
                ids_materias |= self._idx_materias.get(materia_norm, set())
            if ids_materias:
                sets_activos.append(ids_materias)

        # ── Filtro por lugar ──────────────────────────────────────────────────
        if filtro.lugar:
            ids_lugar: set[str] = set()
            for token in _tokens(filtro.lugar):
                ids_lugar |= self._idx_lugar.get(token, set())
            lugar_norm = _normalizar(filtro.lugar)
            ids_lugar |= self._idx_lugar.get(lugar_norm, set())
            if ids_lugar:
                sets_activos.append(ids_lugar)

        # ── Filtro por rango de años ──────────────────────────────────────────
        if filtro.anio_desde or filtro.anio_hasta:
            ids_anio: set[str] = set()
            for anio_str, ids in self._idx_anio.items():
                try:
                    anio_int = int(anio_str[:4])  # Tomar los primeros 4 dígitos
                except (ValueError, TypeError):
                    continue
                desde_ok = (filtro.anio_desde is None) or (anio_int >= filtro.anio_desde)
                hasta_ok = (filtro.anio_hasta is None) or (anio_int <= filtro.anio_hasta)
                if desde_ok and hasta_ok:
                    ids_anio |= ids
            if ids_anio:
                sets_activos.append(ids_anio)

        # ── Intersección AND de todos los criterios activos ───────────────────
        if not sets_activos:
            # Ningún filtro produjo resultados → retornar corpus completo (fallback)
            print("⚠️ [MetadataFilter] Ningún criterio produjo IDs. Retornando corpus completo.")
            return corpus

        # Intersección: ordenar de menor a mayor para optimizar
        sets_activos.sort(key=lambda s: len(s))
        ids_resultado = sets_activos[0].copy()
        for s in sets_activos[1:]:
            ids_resultado &= s

        print(f"✅ [MetadataFilter] Corpus reducido: {len(ids_resultado)} documentos (desde {len(corpus)}).")

        # ── Fallback: si el resultado es muy pequeño, relajar criterios ───────
        if len(ids_resultado) < 15 and len(sets_activos) > 1:
            # Relajar usando solo el primer criterio (el más específico)
            ids_resultado = sets_activos[0].copy()
            print(f"🔄 [MetadataFilter] Resultado muy pequeño. Relajando a {len(ids_resultado)} docs.")

        # ── Recuperar entidades del índice directo ────────────────────────────
        # Mantener el orden original del corpus (preserva ranking previo)
        ids_set = ids_resultado
        subconjunto = [doc for doc in corpus if doc.id in ids_set]

        # Si el corpus de entrada no contiene todos los IDs (ej: corpus ya acotado),
        # intentar recuperar desde el índice directo
        if not subconjunto:
            subconjunto = [
                self._docs_por_id[id_doc]
                for id_doc in ids_resultado
                if id_doc in self._docs_por_id
            ]

        return subconjunto if subconjunto else corpus
