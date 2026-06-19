"""
Capa de Dominio — Puertos de Salida (Outbound Ports)
=====================================================
Contratos abstractos que definen cómo el dominio se comunica con el exterior.
Estos puertos son implementados por los adaptadores de infraestructura.
"""

from abc import ABC, abstractmethod
from typing import Optional

from Dominio.entidades.documento_patrimonial import DocumentoPatrimonial


class PuertoArchivoPatrimonial(ABC):
    """
    Puerto de Salida (Outbound / Driven Port).
    Define el contrato para acceder a la fuente de datos del Archivo Patrimonial,
    independientemente de si la implementación subyacente es la API REST de AtoM,
    un archivo JSON local, o un Mock para desarrollo.
    """

    @abstractmethod
    async def buscar_por_lenguaje_natural(self, query: str, limite: int = 5) -> list[DocumentoPatrimonial]:
        """
        Realiza una búsqueda semántica o por texto libre sobre el catálogo.
        Retorna una lista de DocumentoPatrimonial ordenados por relevancia descendente.
        """
        ...

    @abstractmethod
    async def obtener_documento_por_codigo(self, codigo: str) -> Optional[DocumentoPatrimonial]:
        """
        Obtiene un documento específico mediante su código de referencia archivístico
        (ej. 'UAH-D-1027') o su slug en el sistema AtoM.
        Retorna None si el documento no existe.
        """
        ...
