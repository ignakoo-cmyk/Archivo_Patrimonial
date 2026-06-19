"""
Chat Context — Entidad de Dominio: SesionChat
================================================
Entidad que representa una sesión conversacional completa.

REGLA DE ORO: Sin imports de Gemini, FastAPI ni ningún framework.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from Dominio.objetos_de_valor.chat import Mensaje, RolMensaje


@dataclass
class SesionChat:
    """
    Entidad que representa una sesión conversacional completa.
    Contiene el historial de mensajes y el contexto de la conversación.

    Es mutable por diseño: el historial crece con cada turno.
    """
    id: str
    historial: list[Mensaje] = field(default_factory=list)

    def agregar_mensaje(self, rol: RolMensaje, contenido: str) -> Mensaje:
        """Añade un nuevo mensaje al historial y lo retorna."""
        mensaje = Mensaje(rol=rol, contenido=contenido, id_sesion=self.id)
        self.historial.append(mensaje)
        return mensaje

    @property
    def ultimo_mensaje_usuario(self) -> Optional[Mensaje]:
        """Retorna el último mensaje del usuario en el historial, o None."""
        for mensaje in reversed(self.historial):
            if mensaje.rol == RolMensaje.USUARIO:
                return mensaje
        return None

    @property
    def longitud(self) -> int:
        """Número total de mensajes en la sesión."""
        return len(self.historial)
