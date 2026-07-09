"""
Capa de Aplicación — Puertos de Entrada (Inbound / Driving Ports)
=================================================================
Contratos abstractos que los Adaptadores de Entrada (ej. FastAPI Controllers)
utilizan para comunicarse con la capa de Aplicación.

Beneficio clave de este contrato:
  - El controlador HTTP solo conoce la interfaz, nunca la implementación concreta.
  - Permite swappear la implementación (ej. para tests) sin tocar el controlador.
  - El sistema es completamente testeable sin levantar infraestructura HTTP.

REGLA DE ORO: Solo Python estándar (abc). Sin imports de FastAPI ni frameworks.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class PuertoBuscadorDocumentos(ABC):
    """
    Puerto de Entrada — Caso de Uso del AtoM Integration Context.

    Define el contrato de operaciones que el sistema expone hacia el exterior
    (controladores HTTP, CLI, tests de integración). Los adaptadores de entrada
    dependen de esta abstracción, no de la implementación concreta.

    Implementado por:
      - BuscadorDocumentosUseCase → implementación de producción.
      - MockBuscadorDocumentos    → implementación ligera para tests unitarios.
    """

    @abstractmethod
    async def ejecutar_busqueda(self, query: str, limite: int = 5) -> dict:
        """
        Punto de entrada para consultas en lenguaje natural.

        Args:
            query:  Texto de la consulta en lenguaje natural del usuario.
            limite: Número máximo de resultados a retornar.

        Returns:
            Diccionario serializable con 'mensaje', 'documentos', 'rich_cards',
            'quick_replies' y 'total'. Listo para ser enviado como respuesta HTTP.
        """
        ...

    @abstractmethod
    async def obtener_detalle(self, codigo: str) -> dict:
        """
        Obtiene el detalle de un documento específico por código de referencia.

        Args:
            codigo: Código de referencia archivístico (ej. 'UAH-D-1027') o slug.

        Returns:
            Diccionario serializable con 'mensaje', 'documento', 'rich_card'
            y 'quick_replies'. Si no existe, 'documento' será None.
        """
        ...
