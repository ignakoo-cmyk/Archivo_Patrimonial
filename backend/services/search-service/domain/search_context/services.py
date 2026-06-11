"""
Search Context — Servicio de Dominio: GestorBusqueda
======================================================
Centraliza la Búsqueda Híbrida Inteligente y el algoritmo RRF.
Opera exclusivamente con abstracciones (Puertos). No conoce ChromaDB,
scikit-learn ni ninguna librería concreta.
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.search_context.models import Consulta, DocumentoPatrimonial, ResultadoBusqueda
from domain.search_context.ports import AtoMRepositoryPort, LexicalSearchPort, VectorStorePort

# Constantes del algoritmo RRF — parte del conocimiento del dominio de búsqueda
_RRF_K: int = 60
_PESO_EXACTO: float = 1.5
_PESO_SEMANTICO: float = 1.2
_PESO_LEXICO: float = 1.0


@dataclass
class GestorBusqueda:
    """
    Servicio de Dominio que orquesta la Búsqueda Híbrida.

    Tres estrategias fusionadas con RRF (Reciprocal Rank Fusion):
      1. Coincidencia Exacta — Python puro, sin librerías.
      2. Semántica           — delega a VectorStorePort (ChromaDB).
      3. Léxica              — delega a LexicalSearchPort (TF-IDF).
    """
    almacen_vectorial: VectorStorePort
    indice_lexico: LexicalSearchPort
    repositorio: AtoMRepositoryPort

    def buscar(self, consulta: Consulta) -> list[ResultadoBusqueda]:
        """Ejecuta las tres estrategias y fusiona rankings con RRF."""
        todos = self.repositorio.obtener_todos()

        exactos  = self._buscar_exacto(consulta.texto_normalizado, todos)
        semanticos = self.almacen_vectorial.buscar_similares(consulta.texto, n_resultados=15)
        lexicos    = self.indice_lexico.buscar_por_terminos(consulta.texto, n_resultados=15)

        tabla_rrf: dict[str, float] = {}
        self._aplicar_rrf(exactos,    _PESO_EXACTO,    tabla_rrf)
        self._aplicar_rrf(semanticos, _PESO_SEMANTICO, tabla_rrf)
        self._aplicar_rrf(lexicos,    _PESO_LEXICO,    tabla_rrf)

        ids_ordenados = sorted(tabla_rrf.items(), key=lambda p: p[1], reverse=True)

        resultados: list[ResultadoBusqueda] = []
        for id_doc, puntuacion in ids_ordenados[: consulta.limite]:
            doc = self.repositorio.obtener_por_id(id_doc)
            if doc:
                resultados.append(ResultadoBusqueda(documento=doc, puntuacion_rrf=round(puntuacion, 6)))

        return resultados

    # ── Métodos privados de dominio ────────────────────────────────────────────

    @staticmethod
    def _buscar_exacto(texto: str, docs: list[DocumentoPatrimonial]) -> list[DocumentoPatrimonial]:
        candidatos: list[tuple[DocumentoPatrimonial, float]] = []
        for doc in docs:
            titulo = doc.titulo.lower()
            if texto == titulo:
                candidatos.append((doc, 1.0))
            elif texto in titulo:
                candidatos.append((doc, 0.9))
        return [d for d, _ in sorted(candidatos, key=lambda x: x[1], reverse=True)]

    @staticmethod
    def _aplicar_rrf(
        docs: list[DocumentoPatrimonial],
        peso: float,
        tabla: dict[str, float],
        k: int = _RRF_K,
    ) -> None:
        for rango, doc in enumerate(docs):
            tabla[doc.id] = tabla.get(doc.id, 0.0) + peso * (1.0 / (k + rango + 1))
