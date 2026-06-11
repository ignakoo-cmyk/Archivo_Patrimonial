"""
Capa de Aplicacion -- Puertos (Interfaces)
=============================================
Contratos abstractos que definen como el dominio se comunica con el exterior.
Estos puertos son implementados por los adaptadores de infraestructura.

Clasificacion:
- Outbound Ports (Driven): definen lo que el dominio necesita del mundo externo.
  Los adaptadores que los implementan se inyectan en los casos de uso.
"""

from abc import ABC, abstractmethod
from typing import Optional
from domain.models import DocumentoPatrimonial


class PuertoArchivoPatrimonial(ABC):
    """
    Puerto de Salida (Outbound / Driven Port).
    Define el contrato para acceder a la fuente de datos del Archivo Patrimonial,
    independientemente de si la implementacion subyacente es la API REST de AtoM,
    un archivo JSON local, o un Mock para desarrollo.
    """

    @abstractmethod
    async def buscar_por_lenguaje_natural(self, query: str, limite: int = 5) -> list[DocumentoPatrimonial]:
        """
        Realiza una busqueda semantica o por texto libre sobre el catalogo.
        Retorna una lista de DocumentoPatrimonial ordenados por relevancia descendente.
        """
        ...

    @abstractmethod
    async def obtener_documento_por_codigo(self, codigo: str) -> Optional[DocumentoPatrimonial]:
        """
        Obtiene un documento especifico mediante su codigo de referencia archivistico
        (ej. 'UAH-D-1027') o su slug en el sistema AtoM.
        Retorna None si el documento no existe.
        """
        ...
