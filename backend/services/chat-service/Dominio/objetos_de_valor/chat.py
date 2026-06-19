"""
Chat Context — Objetos de Valor
=================================
Objetos de Valor inmutables del Bounded Context de Interacción Conversacional.

Lenguaje Ubicuo de este contexto:
  - Mensaje:              unidad atómica de comunicación (usuario o asistente).
  - PromptContextualizado: prompt final ensamblado con contexto RAG listo para el LLM.

REGLA DE ORO: Sin imports de Gemini, FastAPI ni ningún framework.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RolMensaje(str, Enum):
    """Rol del emisor dentro de una sesión de chat."""
    USUARIO    = "usuario"
    ASISTENTE  = "asistente"
    SISTEMA    = "sistema"


class IntencionUsuario(str, Enum):
    """
    Clasificación semántica de la intención del mensaje del usuario.
    Usada por evaluar_intencion_usuario() para decidir el flujo de RAG.
    """
    SALUDO_O_GENERAL  = "saludo_o_general"   # Saludos, preguntas genéricas, presentación
    BUSQUEDA_ARCHIVO  = "busqueda_archivo"    # Requiere RAG sobre el archivo patrimonial
    FUERA_DE_AMBITO   = "fuera_de_ambito"     # Pregunta completamente ajena al archivo


@dataclass(frozen=True)
class Mensaje:
    """
    Objeto de Valor inmutable que representa un turno en la conversación.
    Una vez creado, un mensaje no cambia.
    """
    rol: RolMensaje
    contenido: str
    id_sesion: str

    def __post_init__(self) -> None:
        if not self.contenido or not self.contenido.strip():
            raise ValueError("El contenido de un Mensaje no puede estar vacío.")
        if not self.id_sesion:
            raise ValueError("Un Mensaje debe pertenecer a una sesión.")


@dataclass(frozen=True)
class PromptContextualizado:
    """
    Objeto de Valor que encapsula el prompt final listo para enviar al LLM.
    Resultado del ensamblado por ChatOrchestratorService usando contexto RAG.

    Separa la construcción del prompt (dominio) del envío real (adaptador).
    """
    texto_completo: str
    n_documentos_contexto: int
    requirio_busqueda: bool

    def __post_init__(self) -> None:
        if not self.texto_completo.strip():
            raise ValueError("El PromptContextualizado no puede estar vacío.")
        if self.n_documentos_contexto < 0:
            raise ValueError("El número de documentos de contexto no puede ser negativo.")
