"""
Adaptador de Salida — StaticJsonRepositoryAdapter (JSON Estático)
==================================================================
Implementa AtoMRepositoryPort leyendo el catálogo completo desde
``Infraestructura/datos/clean_with_metadata.json`` en memoria.

Estrategia de carga:
- **Eager**: todos los documentos se cargan en __init__ (síncrono),
  de modo que los métodos async obtener_todos / obtener_por_id
  devuelven datos en RAM de forma instantánea — sin I/O adicional.

Campos Dublin Core mapeados (v3):
- dc:creator  → DocumentoPatrimonial.creator
- dc:subject  → DocumentoPatrimonial.materias
- dc:coverage → DocumentoPatrimonial.lugar
- categories  → DocumentoPatrimonial.categorias

Validación:
- Cada entrada del JSON es validada con el modelo Pydantic interno
  ``_EntradaJsonRaw`` antes de mapear al dominio. Las entradas con
  datos inválidos (título vacío, id ausente) se omiten con log.

Extensibilidad:
    Este adaptador es el repositorio de desarrollo/producción actual.
    Cuando se active la integración real con AtoM, crear:
      Infraestructura/adaptadores_salida/atom_api_adaptador.py
    implementando AtoMRepositoryPort con httpx.AsyncClient.
    Sustituir en main.py (Composition Root). Este archivo queda intacto.

REGLA: Solo depende de AtoMRepositoryPort (Dominio). Sin FastAPI, sin
       dependencias de otras capas de Infraestructura.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from Dominio.puertos.repositorio_salida import AtoMRepositoryPort
from Dominio.entidades.documento_patrimonial import DocumentoPatrimonial


# ─────────────────────────────────────────────────────────────────────────────
# Modelo Pydantic interno — validación de entradas del JSON crudo
# No se expone fuera de este módulo (prefijo _ por convención).
# ─────────────────────────────────────────────────────────────────────────────

class _EntradaJsonRaw(BaseModel):
    """
    Modelo de validación para cada registro del JSON de metadatos.
    Refleja el esquema real exportado por el scraper/AtoM.
    Campos opcionales cubren variaciones entre versiones del JSON.
    """

    id: Optional[Any] = None
    slug: Optional[str] = None
    title: str = Field(default="")
    description: Optional[str] = ""
    href: Optional[str] = ""
    year: Optional[str] = None
    date: Optional[str] = None

    # Dublin Core
    dc_creator: list[Any] = Field(default_factory=list, alias="dc:creator")
    dc_subject: list[Any] = Field(default_factory=list, alias="dc:subject")
    dc_coverage: list[Any] = Field(default_factory=list, alias="dc:coverage")
    categories: list[Any] = Field(default_factory=list)

    model_config = {"populate_by_name": True}

    @field_validator("title", mode="before")
    @classmethod
    def titulo_no_vacio(cls, v: Any) -> str:
        return str(v).strip() if v else ""


# ─────────────────────────────────────────────────────────────────────────────
# Funciones privadas de transformación Dublin Core (módulo-nivel)
# Cada función tiene una responsabilidad única → CC ≤ 3 (grado A/B)
# ─────────────────────────────────────────────────────────────────────────────

def _extraer_creator(dc_creator: list) -> tuple[str | None, set[str]]:
    """
    Extrae el creator principal y el vocabulario completo de dc:creator.
    Retorna (creator_str, vocabulario_set).
    Acepta tanto lista de dicts como lista de strings planos.
    """
    if not dc_creator:
        return None, set()

    vocabulario: set[str] = set()

    def _str_creator(item) -> str:
        if isinstance(item, dict):
            return (item.get("authorized_form_of_name") or item.get("name", "")).strip()
        return str(item).strip()

    primer_str = _str_creator(dc_creator[0]) or None

    for c in dc_creator:
        c_str = _str_creator(c)
        if c_str:
            vocabulario.add(c_str)

    return primer_str, vocabulario


def _extraer_materias(dc_subject: list) -> str | None:
    """
    Convierte dc:subject a string separado por ' | '.
    Acepta tanto lista de dicts como lista de strings planos.
    """
    if not dc_subject:
        return None

    if isinstance(dc_subject[0], dict):
        partes = [
            s.get("name", "") or s.get("authorized_form_of_name", "")
            for s in dc_subject if s
        ]
    else:
        partes = [str(s) for s in dc_subject if s]

    return " | ".join(p.strip() for p in partes if p.strip()) or None


def _extraer_lugar(dc_coverage: list) -> str | None:
    """
    Extrae la primera cobertura geográfica de dc:coverage.
    Acepta tanto dict como string plano.
    """
    if not dc_coverage:
        return None

    primer = dc_coverage[0]
    if isinstance(primer, dict):
        return (primer.get("name") or primer.get("authorized_form_of_name", "")).strip() or None
    return str(primer).strip() or None


def _extraer_categorias(categories: list) -> str | None:
    """
    Convierte el árbol de categorías archivísticas a string para búsqueda de texto.
    Acepta tanto lista de dicts como lista de strings planos.
    """
    if not categories:
        return None

    if isinstance(categories[0], dict):
        partes = [c.get("name", "") for c in categories if c.get("name")]
    else:
        partes = [str(c) for c in categories if c]

    return " ".join(p.strip() for p in partes if p.strip()) or None


# ─────────────────────────────────────────────────────────────────────────────
# Método de mapeo refactorizado (CC = 1, grado A)
# ─────────────────────────────────────────────────────────────────────────────

class StaticJsonRepositoryAdapter(AtoMRepositoryPort):
    """
    Adaptador estático que cumple AtoMRepositoryPort mediante carga
    en memoria del archivo JSON de metadatos patrimoniales.

    Los métodos públicos son async (contrato del puerto) pero devuelven
    datos ya en RAM — sin suspensión real del event-loop.
    """

    def __init__(
        self,
        ruta_json: str = "Infraestructura/datos/clean_with_metadata.json",
    ) -> None:
        """
        Args:
            ruta_json: Ruta relativa o absoluta al JSON de metadatos.
                       Cambia mediante variable de entorno DATA_PATH en main.py.
        """
        self._ruta_json = ruta_json
        self._documentos: list[DocumentoPatrimonial] = []
        self._indice_por_id: dict[str, DocumentoPatrimonial] = {}
        self._vocabulario_creators: set[str] = set()
        self._cargar_memoria()

    # ── Implementación del contrato AtoMRepositoryPort (async) ───────────────

    async def obtener_todos(self) -> list[DocumentoPatrimonial]:
        """
        Retorna el catálogo completo cargado en RAM.
        Async por contrato del puerto; no suspende el event-loop.
        """
        return self._documentos

    async def obtener_por_id(self, id_documento: str) -> Optional[DocumentoPatrimonial]:
        """
        Búsqueda O(1) por ID o slug usando el índice en memoria.
        Async por contrato del puerto; no suspende el event-loop.

        Args:
            id_documento: ID numérico (como string) o slug del documento.

        Returns:
            DocumentoPatrimonial si existe, None si no se encontró.
        """
        return self._indice_por_id.get(id_documento)

    # ── Propiedad adicional (no es parte del puerto; usada por main.py) ───────

    @property
    def vocabulario_creators(self) -> set[str]:
        """
        Conjunto de todos los dc:creator únicos del corpus.
        Usado por NLPExtractorAdapter para matching exacto de actores.
        No forma parte de AtoMRepositoryPort — es una capacidad específica
        de este adaptador JSON que main.py aprovecha en la composición.
        """
        return self._vocabulario_creators

    # ── Métodos privados de infraestructura ───────────────────────────────────

    def _cargar_memoria(self) -> None:
        """
        Carga eager del JSON en memoria. Se ejecuta UNA vez en __init__.
        Utiliza Pydantic para validar cada entrada antes de mapear al dominio.
        """
        if not os.path.exists(self._ruta_json):
            print(f"⚠️ [StaticJsonRepo] Archivo no encontrado: {self._ruta_json}")
            return

        try:
            with open(self._ruta_json, "r", encoding="utf-8", errors="ignore") as f:
                datos_crudos: list[dict] = json.load(f)
        except Exception as error:
            print(f"❌ [StaticJsonRepo] Error leyendo JSON: {error}")
            return

        omitidos = 0
        for idx, item in enumerate(datos_crudos):
            # Validar con Pydantic — entradas malformadas se omiten
            try:
                entrada = _EntradaJsonRaw.model_validate(item)
            except Exception:
                omitidos += 1
                continue

            if not entrada.title:
                omitidos += 1
                continue

            doc = self._mapear_a_entidad(entrada, idx)
            if doc is None:
                omitidos += 1
                continue

            self._documentos.append(doc)
            self._indice_por_id[doc.id] = doc
            # Indexar también por slug para recuperación O(1)
            if entrada.slug and entrada.slug != doc.id:
                self._indice_por_id[entrada.slug] = doc

        print(
            f"✅ [StaticJsonRepo] {len(self._documentos)} documentos cargados | "
            f"{omitidos} omitidos | "
            f"{len(self._vocabulario_creators)} creators únicos registrados."
        )

    def _mapear_a_entidad(
        self, entrada: _EntradaJsonRaw, idx: int
    ) -> Optional[DocumentoPatrimonial]:
        """
        Traduce una _EntradaJsonRaw (ya validada por Pydantic) al tipo de
        dominio DocumentoPatrimonial.

        Refactorización P3: cada campo Dublin Core se delega a una función
        privada del módulo con CC ≤ 3. Esta función queda en CC = 1 (grado A).
        Retorna None si falla la invariante del dominio.
        """
        id_doc = str(entrada.id) if entrada.id is not None else (entrada.slug or str(idx))

        creator_str, vocab = _extraer_creator(entrada.dc_creator)
        self._vocabulario_creators |= vocab

        try:
            return DocumentoPatrimonial(
                id=id_doc,
                titulo=entrada.title,
                descripcion=entrada.description or "",
                url_catalogo=entrada.href or "",
                anio=entrada.year or entrada.date,
                creator=creator_str,
                materias=_extraer_materias(entrada.dc_subject),
                lugar=_extraer_lugar(entrada.dc_coverage),
                categorias=_extraer_categorias(entrada.categories),
            )
        except ValueError:
            # Falla de invariante del dominio (id o título vacíos) — omitir
            return None
