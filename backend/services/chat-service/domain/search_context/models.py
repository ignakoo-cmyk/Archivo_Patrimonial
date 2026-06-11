"""
Search Context — Modelo Compartido (Chat Service)
==================================================
Proyección mínima del DocumentoPatrimonial que necesita el Chat Context.
El chat-service no construye ni busca documentos: sólo los consume para RAG.

REGLA: Sin imports de frameworks ni librerías externas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DocumentoPatrimonial:
    """
    Proyección de sólo lectura de un registro del archivo patrimonial.
    Usada por el Chat Context para construir el contexto RAG y generar citas.

    Campos clave para el pipeline RAG:
      - descripcion:   texto que se inyecta como contexto en el prompt.
      - url_catalogo:  URL usada para generar citas obligatorias en la respuesta.
    """
    id: str
    titulo: str
    descripcion: str
    url_catalogo: str
    puntuacion_relevancia: float = 0.0
    anio: Optional[str] = None

    @property
    def tiene_url(self) -> bool:
        """Indica si el documento tiene URL disponible para citar."""
        return bool(self.url_catalogo and self.url_catalogo.strip())

    @property
    def resumen_para_prompt(self) -> str:
        """Texto compacto del documento para inyectar en el prompt del LLM."""
        anio_str = f" ({self.anio})" if self.anio else ""
        return (
            f"Título: {self.titulo}{anio_str}\n"
            f"Descripción: {self.descripcion}\n"
            f"URL: {self.url_catalogo if self.tiene_url else 'No disponible'}"
        )
