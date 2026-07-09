"""
Adaptador de Salida — Repositorio de Sesiones en Memoria
==========================================================
Implementa SesionRepositorioPort usando un diccionario Python en RAM.

Esta es la implementación de desarrollo/baja escala. Para producción
con alta concurrencia, reemplazar por RedisSesionRepositorio sin tocar
ninguna otra capa del sistema — solo cambiar esta línea en el main.py:

  # Antes:
  sesion_repo = InMemorySesionRepositorio()

  # Después (producción):
  sesion_repo = RedisSesionRepositorio(redis_url=os.getenv("REDIS_URL"))

El dominio y los controladores no requieren ningún cambio.
"""

from __future__ import annotations

from typing import Optional

from Dominio.entidades.sesion_chat import SesionChat
from Dominio.puertos.puertos_salida import SesionRepositorioPort


class InMemorySesionRepositorio(SesionRepositorioPort):
    """
    Implementación concreta de SesionRepositorioPort que almacena
    las sesiones en un diccionario Python en memoria (RAM).

    Limitaciones conocidas (aceptables para desarrollo):
      - No es persistente: las sesiones se pierden al reiniciar el servidor.
      - No es thread-safe para escrituras concurrentes masivas.
      - No escala horizontalmente (cada instancia tiene su propio estado).

    Para producción con múltiples réplicas, implementar RedisSesionRepositorio.
    """

    def __init__(self) -> None:
        self._sesiones: dict[str, SesionChat] = {}

    def obtener_o_crear(self, id_sesion: str) -> SesionChat:
        """
        Retorna la sesión existente o crea e indexa una nueva automáticamente.
        """
        if id_sesion not in self._sesiones:
            self._sesiones[id_sesion] = SesionChat(id=id_sesion)
        return self._sesiones[id_sesion]

    def guardar(self, sesion: SesionChat) -> None:
        """
        Persiste la sesión en el diccionario en memoria.
        Como el dict es mutable y la sesión es la misma referencia,
        en esta implementación la operación es un no-op (ya está en memoria),
        pero el contrato se mantiene para compatibilidad con otras implementaciones.
        """
        self._sesiones[sesion.id] = sesion

    def obtener(self, id_sesion: str) -> Optional[SesionChat]:
        """Retorna la sesión si existe, None en caso contrario."""
        return self._sesiones.get(id_sesion)
