# Adaptadores de Salida (Driven Adapters) — Infraestructura concreta
from Infraestructura.adaptadores_salida.gemini_adaptador import GeminiAdapter
from Infraestructura.adaptadores_salida.servicio_busqueda_adaptador import SearchServiceHttpAdapter
from Infraestructura.adaptadores_salida.sesion_en_memoria_adaptador import InMemorySesionRepositorio

__all__ = ["GeminiAdapter", "SearchServiceHttpAdapter", "InMemorySesionRepositorio"]
