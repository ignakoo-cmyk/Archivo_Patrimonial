"""
Search Context (vista desde el Chat Service)
=============================================
Modelos de sólo lectura del archivo patrimonial que el chat-service
necesita para construir el contexto RAG. Son una proyección del Search Context
para este Bounded Context: sin lógica de búsqueda, sólo la estructura de datos
que el orquestador de chat necesita conocer.
"""
from domain.search_context.models import DocumentoPatrimonial

__all__ = ["DocumentoPatrimonial"]
