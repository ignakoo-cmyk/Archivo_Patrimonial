"""
Chat Context — Puertos de Salida (Outbound Ports)
==================================================
Contratos abstractos que definen lo que el Chat Context necesita
del mundo exterior. Cada interfaz es una "promesa" que un adaptador
de infraestructura debe cumplir.

Puertos definidos:
  - ModeloLenguajePort:      abstrae el LLM generativo (Gemini, OpenAI, etc.).
  - ServicioBusquedaPort:    abstrae la comunicación con el search-service.
  - SesionRepositorioPort:   abstrae el almacén de sesiones (en memoria, Redis, etc.).

REGLA DE ORO: Sin imports de google.generativeai, httpx ni ningún framework.
Solo Python estándar y tipos del dominio propio.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from Dominio.objetos_de_valor.chat import PromptContextualizado
from Dominio.entidades.documento_patrimonial import DocumentoPatrimonial
from Dominio.entidades.sesion_chat import SesionChat


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
    ) -> tuple[list[DocumentoPatrimonial], int, dict[str, list[str]]]:
        """
        Recupera los documentos más relevantes del archivo patrimonial
        para una consulta dada.

        Args:
            consulta: Texto de la pregunta del usuario.
            limite:   Número máximo de documentos a recuperar.

        Returns:
            Tupla conteniendo:
            1. Lista de DocumentoPatrimonial ordenados por relevancia.
            2. Total de documentos en el corpus pre-filtrado.
            3. Diccionario de facetas sugeridas.
            Si el servicio falla, retorna ([], 0, {}).
        """
        ...


class SesionRepositorioPort(ABC):
    """
    Puerto de Salida — Repositorio de Sesiones de Chat.

    Abstrae el almacenamiento del estado de las conversaciones activas.
    El Chat Context no sabe si las sesiones se guardan en memoria,
    Redis, una base de datos SQL u otro mecanismo.

    Implementado por:
      - InMemorySesionRepositorio → dict en RAM (desarrollo / baja concurrencia).
      - RedisSesionRepositorio    → Redis persistente (producción / alta concurrencia).

    Contratos de ciclo de vida:
      - Cada sesión tiene un ID único (conversation_id del frontend).
      - Si la sesión no existe, obtener_o_crear() la inicializa automáticamente.
    """

    @abstractmethod
    def obtener_o_crear(self, id_sesion: str) -> SesionChat:
        """
        Retorna la sesión existente o crea una nueva si no existe.

        Args:
            id_sesion: Identificador único de la conversación (del frontend).

        Returns:
            La SesionChat correspondiente al id_sesion.
        """
        ...

    @abstractmethod
    def guardar(self, sesion: SesionChat) -> None:
        """
        Persiste el estado actual de la sesión.

        Args:
            sesion: Entidad SesionChat con el historial actualizado.
        """
        ...

    @abstractmethod
    def obtener(self, id_sesion: str) -> Optional[SesionChat]:
        """
        Recupera una sesión existente sin crearla.

        Args:
            id_sesion: Identificador único de la conversación.

        Returns:
            La SesionChat si existe, None si no se encontró.
        """
        ...
