"""
Capa de Dominio — Entidad Raíz de Agregado: DocumentoPatrimonial
=================================================================
Entidad central del AtoM Integration Context. Representa un registro
del Archivo Patrimonial de la UAH mapeado desde el esquema Dublin Core
que utiliza AtoM internamente.

Campos clave para el sistema RAG:
  - alcance_y_contenido: texto largo necesario para generar resúmenes contextuales.
  - codigo_referencia:   identificador archivístico único (ej. 'UAH-D-1027').

REGLA DE ORO: Solo Python estándar. Sin imports de Pydantic, FastAPI
ni ninguna librería de terceros. Esta entidad es el núcleo del dominio
y debe ser completamente independiente de la infraestructura.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from Dominio.objetos_de_valor.objeto_digital import ObjetoDigital


@dataclass
class DocumentoPatrimonial:
    """
    Entidad Raíz de Agregado (Aggregate Root) del AtoM Integration Context.
    Representa un registro completo del Archivo Patrimonial de la UAH.

    Es mutable por diseño: el campo 'relevancia' es asignado por el motor
    de búsqueda DESPUÉS de la construcción, reflejando la posición en los
    resultados de la consulta.

    Campos Dublin Core soportados:
      - creadores  → dc:creator  (persona/institución autora del documento)
      - materias   → dc:subject  (descriptores temáticos del tesauro)
      - cobertura  → dc:coverage (cobertura geográfica o temporal)
    """
    id: str
    titulo: str
    codigo_referencia: str = ""
    anio: Optional[str] = None
    url_sistema: str = ""
    alcance_y_contenido: str = ""
    creadores: list[str] = field(default_factory=list)
    materias: list[str] = field(default_factory=list)
    cobertura: list[str] = field(default_factory=list)
    objetos_digitales: list[ObjetoDigital] = field(default_factory=list)
    relevancia: float = 0.0

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise ValueError("DocumentoPatrimonial requiere un ID único no vacío.")
        if not self.titulo or not self.titulo.strip():
            raise ValueError("DocumentoPatrimonial requiere un título no vacío.")
        if self.relevancia < 0.0:
            raise ValueError("La relevancia no puede ser negativa.")

    @property
    def miniatura(self) -> Optional[ObjetoDigital]:
        """Retorna el primer objeto digital de tipo imagen, o None."""
        for obj in self.objetos_digitales:
            if obj.es_imagen:
                return obj
        return None

    @property
    def descripcion_corta(self) -> str:
        """Resumen truncado de alcance_y_contenido para vistas de lista."""
        if len(self.alcance_y_contenido) > 180:
            return self.alcance_y_contenido[:180] + "..."
        return self.alcance_y_contenido

    @property
    def tiene_url(self) -> bool:
        """Indica si el documento posee URL permanente en el catálogo."""
        return bool(self.url_sistema and self.url_sistema.strip())
