"""
Search Context — Bounded Context de Recuperación de Información
================================================================
Expone los tres módulos del contexto:
  - models:   Entidades y Objetos de Valor del dominio de búsqueda.
  - ports:    Contratos (interfaces) de salida del contexto.
  - services: Servicio de dominio GestorBusqueda con algoritmo RRF.
"""
from domain.search_context.models import (
    Consulta,
    DocumentoPatrimonial,
    ResultadoBusqueda,
)

__all__ = ["Consulta", "DocumentoPatrimonial", "ResultadoBusqueda"]
