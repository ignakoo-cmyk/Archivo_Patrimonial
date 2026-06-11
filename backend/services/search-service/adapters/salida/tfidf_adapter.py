"""
Adaptador de Salida — TF-IDF (scikit-learn)
=============================================
Implementa LexicalSearchPort utilizando TfidfVectorizer de scikit-learn.

Responsabilidades:
- Construir el índice TF-IDF en memoria a partir de los documentos del dominio.
- Realizar búsquedas léxicas por similitud coseno sobre dicho índice.

TODO el código dependiente de scikit-learn se concentra aquí.
Si se migra a BM25 u otro algoritmo léxico, SOLO este archivo cambia.
"""

from __future__ import annotations

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from application.puertos.salida import LexicalSearchPort
from domain.search_context.models import DocumentoPatrimonial


class TFIDFAdapter(LexicalSearchPort):
    """
    Adaptador de Salida concreto para búsqueda léxica con TF-IDF.

    Implementa el contrato LexicalSearchPort usando scikit-learn.
    El índice se construye en memoria al iniciar el servicio a partir de
    los documentos provenientes del repositorio.
    """

    def __init__(self, idioma_stopwords: str = "english") -> None:
        """
        Args:
            idioma_stopwords: Idioma para filtrar stop-words en el vectorizador.
                              Usar 'english' por defecto (scikit-learn no incluye
                              español nativo; se puede extender con lista custom).
        """
        self._vectorizador = TfidfVectorizer(
            stop_words=idioma_stopwords,
            max_features=5000,
        )
        self._matriz_tfidf = None
        self._documentos_indexados: list[DocumentoPatrimonial] = []

    # ──────────────────────────────────────────────────────────
    # Implementación del contrato LexicalSearchPort
    # ──────────────────────────────────────────────────────────

    def construir_indice(self, documentos: list[DocumentoPatrimonial]) -> None:
        """
        Construye el índice TF-IDF en memoria.
        Debe llamarse una vez al iniciar el servicio (en el lifespan de FastAPI).

        Args:
            documentos: Lista completa de DocumentoPatrimonial del repositorio.
        """
        if not documentos:
            print("⚠️ [TFIDFAdapter] No se recibieron documentos para indexar.")
            return

        self._documentos_indexados = documentos
        textos = [doc.texto_indexable for doc in documentos]

        try:
            self._matriz_tfidf = self._vectorizador.fit_transform(textos)
            print(
                f"✅ [TFIDFAdapter] Índice TF-IDF construido "
                f"con {len(documentos)} documentos."
            )
        except Exception as error:
            print(f"⚠️ [TFIDFAdapter] Error construyendo índice TF-IDF: {error}")
            self._matriz_tfidf = None

    def buscar_por_terminos(
        self,
        consulta: str,
        n_resultados: int = 10,
        umbral_minimo: float = 0.05,
    ) -> list[DocumentoPatrimonial]:
        """
        Realiza una búsqueda léxica por similitud coseno TF-IDF.

        Args:
            consulta:       Texto de búsqueda.
            n_resultados:   Máximo de resultados a devolver.
            umbral_minimo:  Puntuación mínima de similitud para incluir resultado.

        Returns:
            Lista de DocumentoPatrimonial ordenados por similitud descendente.
        """
        if self._matriz_tfidf is None or not self._documentos_indexados:
            return []

        try:
            vector_consulta = self._vectorizador.transform([consulta])
            similitudes = cosine_similarity(
                vector_consulta, self._matriz_tfidf
            ).flatten()
        except Exception as error:
            print(f"❌ [TFIDFAdapter] Error en búsqueda léxica: {error}")
            return []

        # Obtener índices con mayor similitud (Top N)
        indices_top = similitudes.argsort()[-n_resultados:][::-1]

        resultados: list[DocumentoPatrimonial] = []
        for idx in indices_top:
            if similitudes[idx] >= umbral_minimo:
                resultados.append(self._documentos_indexados[idx])

        return resultados
