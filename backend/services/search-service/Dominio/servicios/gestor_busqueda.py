"""
Search Context — Servicio de Dominio: GestorBusqueda
======================================================
Centraliza la Búsqueda Híbrida Inteligente y el algoritmo RRF.
Opera exclusivamente con abstracciones (Puertos). No conoce ChromaDB,
scikit-learn ni ninguna librería concreta.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from Dominio.entidades.documento_patrimonial import DocumentoPatrimonial
from Dominio.objetos_de_valor.busqueda import Consulta, RespuestaBusquedaDominio, ResultadoBusqueda
from Dominio.puertos.repositorio_salida import AtoMRepositoryPort, LexicalSearchPort, MetadataFilterPort, VectorStorePort

# Constantes del algoritmo RRF — parte del conocimiento del dominio de búsqueda
_RRF_K: int = 60
_PESO_EXACTO: float = 1.5
_PESO_SEMANTICO: float = 1.2
_PESO_LEXICO: float = 1.0


@dataclass
class GestorBusqueda:
    """
    Servicio de Dominio que orquesta la Búsqueda Híbrida.

    Cuatro estrategias fusionadas con RRF (Reciprocal Rank Fusion):
      0. Pre-filtrado por Metadatos  — reduce el corpus ANTES del embedding (nuevo).
      1. Coincidencia Exacta         — Python puro, sin librerías.
      2. Semántica                  — delega a VectorStorePort (ChromaDB).
      3. Léxica                     — delega a LexicalSearchPort (TF-IDF).
    """
    almacen_vectorial: VectorStorePort
    indice_lexico: LexicalSearchPort
    repositorio: AtoMRepositoryPort
    motor_filtrado: MetadataFilterPort | None = None  # Puerto de pre-filtrado (opcional)

    async def buscar(self, consulta: Consulta) -> RespuestaBusquedaDominio:
        """Ejecuta pre-filtrado por metadatos y las tres estrategias híbridas fusionadas con RRF."""
        todos = await self.repositorio.obtener_todos()

        # ── Paso 0: Pre-filtrado por metadatos NLP (reduce drásticamente el corpus) ──
        corpus_busqueda = todos
        if self.motor_filtrado and consulta.filtro_nlp and not consulta.filtro_nlp.esta_vacio:
            corpus_busqueda = self.motor_filtrado.aplicar_filtros(
                filtro=consulta.filtro_nlp,
                corpus=todos,
            )
            
        total_corpus = len(corpus_busqueda)
        
        # ── Paso 1: Ejecutar estrategias sobre el corpus acotado ──────────────
        exactos = self._buscar_exacto(consulta.texto_normalizado, corpus_busqueda)

        # ── Búsqueda Semántica Híbrida Real ───────────────────────────────────
        # Flujo: ChromaDB → IDs → Repositorio (PG/JSON) → DocumentoPatrimonial completo.
        # Esto garantiza que los resultados semánticos contengan siempre la
        # 'descripcion' completa y todos los metadatos Dublin Core, independientemente
        # de lo que ChromaDB tenga indexado en sus propios metadatos.
        ids_semanticos = self.almacen_vectorial.buscar_ids_similares(
            consulta.texto, n_resultados=15, filtros=consulta.filtros
        )
        semanticos: list[DocumentoPatrimonial] = []
        for id_sem in ids_semanticos:
            doc_completo = await self.repositorio.obtener_por_id(id_sem)
            if doc_completo:
                semanticos.append(doc_completo)

        lexicos = self.indice_lexico.buscar_por_terminos(consulta.texto, n_resultados=15)

        # ── Paso 2: Fusión RRF ───────────────────────────────────────────────
        tabla_rrf: dict[str, float] = {}
        self._aplicar_rrf(exactos,    _PESO_EXACTO,    tabla_rrf)
        self._aplicar_rrf(semanticos, _PESO_SEMANTICO, tabla_rrf)
        self._aplicar_rrf(lexicos,    _PESO_LEXICO,    tabla_rrf)

        ids_ordenados = sorted(tabla_rrf.items(), key=lambda p: p[1], reverse=True)

        # ── Paso 3: Extracción Dinámica de Facetas de los Top Resultados ──────
        facetas: dict[str, list[str]] = {"materias": [], "lugares": [], "categorias": [], "años": []}
        
        # Si la consulta produjo varios resultados, analizamos los Top 50 para extraer facetas relevantes
        if len(ids_ordenados) > 5:
            ctr_materias = Counter()
            ctr_lugares = Counter()
            ctr_categorias = Counter()
            ctr_anios = Counter()
            
            top_ids_facetas = ids_ordenados[:50]
            for id_doc, _ in top_ids_facetas:
                doc = await self.repositorio.obtener_por_id(id_doc)
                if doc:
                    if doc.materias:
                        for m in doc.materias.split(" | "):
                            if m.strip(): ctr_materias[m.strip()] += 1
                    if doc.lugar:
                        ctr_lugares[doc.lugar.strip()] += 1
                    if doc.categorias:
                        for c in doc.categorias.split(" | "):
                            if c.strip(): ctr_categorias[c.strip()] += 1
                    if doc.anio:
                        ctr_anios[doc.anio.strip()] += 1
                        
            # Omitir sugerir materia si ya se filtró por una en NLP
            tiene_materia = consulta.filtro_nlp and consulta.filtro_nlp.materias
            if not tiene_materia:
                facetas["materias"] = [m for m, _ in ctr_materias.most_common(3)]
            facetas["lugares"] = [l for l, _ in ctr_lugares.most_common(2)]
            facetas["categorias"] = [c for c, _ in ctr_categorias.most_common(3)]
            facetas["años"] = [a for a, _ in ctr_anios.most_common(3)]

        resultados: list[ResultadoBusqueda] = []
        for id_doc, puntuacion in ids_ordenados[: consulta.limite]:
            doc = await self.repositorio.obtener_por_id(id_doc)
            if doc:
                resultados.append(ResultadoBusqueda(documento=doc, puntuacion_rrf=round(puntuacion, 6)))

        return RespuestaBusquedaDominio(
            resultados=resultados,
            total_corpus=total_corpus,
            facetas=facetas
        )

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
