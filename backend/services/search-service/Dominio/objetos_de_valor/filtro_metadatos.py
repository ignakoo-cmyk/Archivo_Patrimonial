"""
Search Context — Objeto de Valor: FiltroMetadatos
==================================================
Encapsula los filtros semánticos extraídos del lenguaje natural del usuario
para pre-acotar el espacio de búsqueda antes de aplicar embeddings.

Taxonomía del Archivo Patrimonial UAH (Dublin Core):
  - actor_creador → dc:creator  (Aylwin, Pinochet, UAH, etc.)
  - materias      → dc:subject  (Derechos humanos, Educación, etc.)
  - lugar         → dc:coverage (Santiago, Chile, etc.)
  - anio_desde    → filtro temporal inferior
  - anio_hasta    → filtro temporal superior

REGLA DE ORO: Solo Python estándar. Sin imports de infraestructura.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class FiltroMetadatos:
    """
    Objeto de Valor inmutable que encapsula los filtros de pre-búsqueda.

    Todos los campos son opcionales: un filtro vacío devuelve el corpus completo.
    La lógica de combinación de filtros (AND) se implementa en el adaptador.

    Uso típico:
        filtro = FiltroMetadatos(
            actor_creador="Aylwin Azócar, Patricio",
            materias=["Derechos humanos", "Democracia"],
            lugar="Santiago",
        )
    """
    actor_creador: Optional[str] = None          # dc:creator — persona/institución
    materias: tuple[str, ...] = field(default=())  # dc:subject — descriptores temáticos
    lugar: Optional[str] = None                  # dc:coverage — cobertura geográfica
    anio_desde: Optional[int] = None             # límite temporal inferior
    anio_hasta: Optional[int] = None             # límite temporal superior

    @property
    def esta_vacio(self) -> bool:
        """Retorna True si no hay ningún filtro activo."""
        return (
            self.actor_creador is None
            and not self.materias
            and self.lugar is None
            and self.anio_desde is None
            and self.anio_hasta is None
        )

    @property
    def resumen(self) -> str:
        """Representación legible del filtro activo (útil para logging)."""
        partes = []
        if self.actor_creador:
            partes.append(f"actor='{self.actor_creador}'")
        if self.materias:
            partes.append(f"materias={list(self.materias)}")
        if self.lugar:
            partes.append(f"lugar='{self.lugar}'")
        if self.anio_desde:
            partes.append(f"desde={self.anio_desde}")
        if self.anio_hasta:
            partes.append(f"hasta={self.anio_hasta}")
        return "FiltroMetadatos(" + ", ".join(partes) + ")" if partes else "FiltroMetadatos(vacío)"
