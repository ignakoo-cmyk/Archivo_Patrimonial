"""
Capa de Aplicación — Implementación del Caso de Uso de Búsqueda
================================================================
BuscarContenidoService implementa el Puerto de Entrada BuscarContenidoUseCase.

Actúa como capa de coordinación entre el controlador HTTP y el dominio.
Este es el lugar correcto para añadir capas transversales (cross-cutting concerns)
sin contaminar la lógica pura del dominio:
  - Registro de auditoría (logs de quién buscó qué)
  - Caché de resultados para consultas frecuentes (Redis)
  - Métricas de latencia y telemetría
"""

from __future__ import annotations

from domain.search_context.models import Consulta, ResultadoBusqueda
from domain.search_context.services import GestorBusqueda
from application.puertos.entrada import BuscarContenidoUseCase


class BuscarContenidoService(BuscarContenidoUseCase):
    """
    Implementación concreta del caso de uso de búsqueda.

    Recibe un GestorBusqueda (Servicio de Dominio) ya ensamblado con sus
    dependencias de infraestructura, y lo invoca a través de la interfaz limpia.
    """

    def __init__(self, gestor: GestorBusqueda) -> None:
        """
        Args:
            gestor: El Servicio de Dominio GestorBusqueda con todos sus
                    Puertos de Salida inyectados (VectorStore, Léxico, Repositorio).
        """
        self._gestor = gestor

    def ejecutar(self, consulta: Consulta) -> list[ResultadoBusqueda]:
        """
        Delega la búsqueda al GestorBusqueda del dominio.

        En este método se pueden añadir capas transversales sin tocar el dominio:

        Ejemplo de caché futura:
            clave = f"busqueda:{consulta.texto_normalizado}:{consulta.limite}"
            if resultado := self._cache.get(clave):
                return resultado
            resultado = self._gestor.buscar(consulta)
            self._cache.set(clave, resultado, ttl=300)
            return resultado
        """
        return self._gestor.buscar(consulta)
