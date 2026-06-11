"""
Chat Context — Puertos de Salida (Outbound Ports)
==================================================
Contratos abstractos que definen lo que el Chat Context necesita
del mundo exterior. Cada interfaz es una "promesa" que un adaptador
de infraestructura debe cumplir.

Puertos definidos:
  - ModeloLenguajePort:   abstrae el LLM generativo (Gemini, OpenAI, etc.).
  - ServicioBusquedaPort: abstrae la comunicación con el search-service.

REGLA DE ORO: Sin imports de google.generativeai, httpx ni ningún framework.
Solo Python estándar y tipos del dominio propio.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from domain.chat_context.models import PromptContextualizado
from domain.search_context.models import DocumentoPatrimonial


class ModeloLenguajePort(ABC):
    """
    Puerto de Salida — Modelo de Lenguaje Generativo (LLM).

    Abstrae completamente el motor de generación de texto.
    El Chat Context llama a este puerto sin saber si usa Gemini, GPT-4 u otro.

    Implementado por:
    - GeminiAdapter       → adaptador de producción (google.generativeai).
    - MockLLMAdapter      → respuestas deterministas para pruebas unitarias.
    """

    @abstractmethod
    async def generar_respuesta(self, prompt: PromptContextualizado) -> str:
        """
        Envía el prompt al LLM y retorna el texto de respuesta generado.

        Args:
            prompt: Objeto de Valor con el prompt ensamblado y su metadata.

        Returns:
            Texto de respuesta generado por el LLM en formato Markdown.

        Raises:
            RuntimeError: Si el LLM no está disponible o retorna error.
        """
        ...

    @abstractmethod
    def esta_disponible(self) -> bool:
        """
        Verifica si el modelo de lenguaje está configurado y operativo.
        Permite al orquestador implementar un fallback sin lanzar excepciones.
        """
        ...


class ServicioBusquedaPort(ABC):
    """
    Puerto de Salida — Servicio de Búsqueda Híbrida.

    Abstrae la comunicación con el search-service. El Chat Context
    no sabe si la búsqueda se realiza via HTTP, gRPC o en memoria.

    Implementado por:
    - SearchServiceHttpAdapter → llama al search-service via httpx.
    - MockBusquedaAdapter      → retorna documentos fijos para pruebas.
    """

    @abstractmethod
    async def buscar_documentos_relevantes(
        self, consulta: str, limite: int = 5
    ) -> list[DocumentoPatrimonial]:
        """
        Recupera los documentos más relevantes del archivo patrimonial
        para una consulta dada.

        Args:
            consulta: Texto de la pregunta del usuario.
            limite:   Número máximo de documentos a recuperar.

        Returns:
            Lista de DocumentoPatrimonial ordenados por relevancia.
            Lista vacía si no hay resultados o el servicio no está disponible.
        """
        ...
