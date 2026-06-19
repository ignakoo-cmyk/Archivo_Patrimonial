"""
Search Context — Objetos de Valor: Consulta y ResultadoBusqueda
================================================================
Objetos de Valor inmutables del Bounded Context de Recuperación de Información.

REGLA DE ORO: Sin imports de FastAPI, ChromaDB, scikit-learn ni ningún framework.
Solo Python estándar.

Lenguaje Ubicuo de este contexto:
  - Consulta:         intención del usuario en lenguaje natural.
  - ResultadoBusqueda: documento fusionado con su puntuación RRF.
"""

from __future__ import annotations

from dataclasses import dataclass

from Dominio.entidades.documento_patrimonial import DocumentoPatrimonial


@dataclass(frozen=True)
class Consulta:
    """
    Objeto de Valor que encapsula una búsqueda del usuario.
    Inmutable: una vez creada, sus atributos no cambian.
    Valida sus propias invariantes de dominio en la construcción.
    """
    texto: str
    limite: int = 5

    def __post_init__(self) -> None:
        if not self.texto or not self.texto.strip():
            raise ValueError("La consulta no puede estar vacía.")
        if not (1 <= self.limite <= 50):
            raise ValueError(
                f"El límite debe estar entre 1 y 50. Recibido: {self.limite}"
            )

    @property
    def texto_normalizado(self) -> str:
        """Texto en minúsculas y sin espacios extremos para comparaciones."""
        return self.texto.strip().lower()


@dataclass(frozen=True)
class ResultadoBusqueda:
    """
    Objeto de Valor que encapsula el producto final del algoritmo RRF.
    Agrupa un documento con su puntuación de relevancia compuesta.
    """
    documento: DocumentoPatrimonial
    puntuacion_rrf: float

    def __post_init__(self) -> None:
        if self.puntuacion_rrf < 0:
            raise ValueError("La puntuación RRF no puede ser negativa.")
