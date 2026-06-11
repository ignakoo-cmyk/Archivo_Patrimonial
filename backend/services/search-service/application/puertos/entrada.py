"""
Puertos de Entrada (Inbound / Driving Ports)
=============================================
Interfaces que los Adaptadores de Entrada (ej. FastAPI Controllers)
utilizan para comunicarse con la capa de Aplicación.

Beneficio clave: hacen al sistema completamente testeable.
Un test puede llamar directamente al UseCase sin levantar un servidor HTTP,
y el controlador puede cambiarse (de FastAPI a Django REST, por ejemplo)
sin tocar la lógica de negocio.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from domain.search_context.models import Consulta, ResultadoBusqueda


class BuscarContenidoUseCase(ABC):
    """
    Puerto de Entrada — Caso de Uso de Búsqueda.

    Define el contrato del único caso de uso de este microservicio.
    Los controladores HTTP solo conocen esta interfaz, nunca la implementación.
    Esto permite cambiar la lógica interna de búsqueda sin tocar los controladores.
    """

    @abstractmethod
    def ejecutar(self, consulta: Consulta) -> list[ResultadoBusqueda]:
        """
        Ejecuta el flujo completo de búsqueda híbrida.

        Args:
            consulta: Objeto de Valor inmutable con el texto y parámetros.

        Returns:
            Lista de ResultadoBusqueda ordenados por puntuación RRF descendente.
        """
        ...
