"""
Adaptador de Salida — TF-IDF (scikit-learn)
=============================================
Implementa LexicalSearchPort utilizando TfidfVectorizer de scikit-learn.

Responsabilidades:
- Construir el índice TF-IDF en memoria a partir de los documentos del dominio.
- Realizar búsquedas léxicas por similitud coseno sobre dicho índice.

TODO el código dependiente de scikit-learn se concentra aquí.
Si se migra a BM25 u otro algoritmo léxico, SOLO este archivo cambia.

Mejoras v2:
- Stop-words en español para el corpus del Archivo Patrimonial UAH.
- N-gramas (1,2) para capturar frases compuestas del dominio histórico
  (ej. "derechos humanos", "colección fotográfica", "fondo documental").
- max_features aumentado a 15000 para mayor cobertura léxica.
- sublinear_tf=True para comprimir la escala de TF y mejorar la discriminación.
"""

from __future__ import annotations

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from Dominio.puertos.repositorio_salida import LexicalSearchPort
from Dominio.entidades.documento_patrimonial import DocumentoPatrimonial


# ─── Stop-words en español curadas para el dominio del Archivo Patrimonial ────
# Incluye preposiciones, artículos, conjunciones y verbos de alta frecuencia
# que no aportan valor discriminativo en búsquedas de archivo histórico.
_STOP_WORDS_ESPANOL: list[str] = [
    "a", "al", "algo", "algunas", "algunos", "ante", "antes", "como", "con",
    "contra", "cual", "cuando", "de", "del", "desde", "donde", "durante",
    "e", "el", "ella", "ellas", "ellos", "en", "entre", "era", "es", "esa",
    "esas", "ese", "eso", "esos", "esta", "estas", "este", "esto", "estos",
    "fue", "ha", "han", "has", "hay", "he", "i", "la", "las", "le", "les",
    "lo", "los", "me", "mi", "mis", "mas", "muy", "ni", "no", "nos",
    "nosotros", "o", "os", "otra", "otras", "otro", "otros", "para", "pero",
    "por", "porque", "que", "quien", "se", "sea", "ser", "si", "sin",
    "sobre", "son", "su", "sus", "tambien", "tanto", "te", "tenia", "ti",
    "tiene", "todo", "todos", "tu", "tus", "un", "una", "unas", "uno",
    "unos", "vosotros", "y", "ya", "yo", "el", "esta", "estas", "este",
    "estos", "u",
]


class TFIDFAdapter(LexicalSearchPort):
    """
    Adaptador de Salida concreto para búsqueda léxica con TF-IDF.

    Implementa el contrato LexicalSearchPort usando scikit-learn.
    El índice se construye en memoria al iniciar el servicio a partir de
    los documentos provenientes del repositorio.

    Mejoras v2:
    - Stop-words en español específicas para el dominio archivístico UAH.
    - N-gramas (1,2) capturan frases compuestas características del dominio.
    - Vocabulario ampliado (15k términos) para mayor cobertura.
    - sublinear_tf normaliza la frecuencia de términos dominantes.
    """

    def __init__(self) -> None:
        self._vectorizador = TfidfVectorizer(
            # Vocabulary
            stop_words=_STOP_WORDS_ESPANOL,
            max_features=15_000,
            # N-gramas: unigramas + bigramas capturan "derechos humanos",
            # "archivo patrimonial", "fondo documental", etc.
            ngram_range=(1, 2),
            # sublinear_tf=True aplica log(1+tf) en lugar de tf cruda.
            # Esto evita que documentos largos dominen el ranking.
            sublinear_tf=True,
            # Ignorar términos que aparecen en más del 95% de documentos
            # (demasiado genéricos) o en menos de 2 documentos (ruido).
            max_df=0.95,
            min_df=2,
            # Normalización L2 por defecto — correcta para similitud coseno.
            norm="l2",
            # Codificación robusta para español con caracteres especiales.
            analyzer="word",
            lowercase=True,
            strip_accents="unicode",
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
        # Usar el texto_indexable enriquecido de cada entidad
        textos = [doc.texto_indexable for doc in documentos]

        try:
            self._matriz_tfidf = self._vectorizador.fit_transform(textos)
            vocab_size = len(self._vectorizador.vocabulary_)
            print(
                f"✅ [TFIDFAdapter] Índice TF-IDF construido con {len(documentos)} documentos "
                f"| Vocabulario: {vocab_size} términos | N-gramas (1,2) | Español."
            )
        except Exception as error:
            print(f"⚠️ [TFIDFAdapter] Error construyendo índice TF-IDF: {error}")
            self._matriz_tfidf = None

    def buscar_por_terminos(
        self,
        consulta: str,
        n_resultados: int = 10,
        umbral_minimo: float = 0.01,
    ) -> list[DocumentoPatrimonial]:
        """
        Realiza una búsqueda léxica por similitud coseno TF-IDF.

        Umbral reducido a 0.01 (desde 0.05) para mayor recall en consultas
        en español donde las puntuaciones TF-IDF brutas son más bajas
        por la mayor riqueza morfológica del idioma.

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
