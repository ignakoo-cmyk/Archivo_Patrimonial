"""
Adaptador de Infraestructura — HTTP Client para AtoM
========================================================
Driven Adapter que implementa PuertoArchivoPatrimonial comunicándose
con la API REST del sistema AtoM (Access to Memory).

Actúa como Anti-Corruption Layer: transforma las respuestas JSON de AtoM
(esquema Dublin Core) hacia las entidades puras del dominio.

Todo el conocimiento del esquema JSON de AtoM está concentrado aquí.
Si AtoM cambia su API, solo este archivo necesita actualizarse.
"""

from __future__ import annotations

from typing import Optional

import httpx

from Dominio.entidades.documento_patrimonial import DocumentoPatrimonial
from Dominio.objetos_de_valor.objeto_digital import ObjetoDigital, TipoMIME
from Dominio.puertos.puerto_archivo_patrimonial import PuertoArchivoPatrimonial


class AtoMHttpAdapter(PuertoArchivoPatrimonial):
    """
    Implementación concreta del puerto PuertoArchivoPatrimonial.
    Se comunica via HTTP con la API REST de AtoM.

    Encapsula todo el conocimiento de:
      - La URL y parámetros de la API de AtoM.
      - La transformación del esquema Dublin Core al modelo de dominio.
      - El manejo de errores HTTP y de red.
    """

    def __init__(self, base_url: str, http_client: httpx.AsyncClient) -> None:
        """
        Args:
            base_url:     URL base de la instancia AtoM (ej. 'http://atom:8081').
            http_client:  Cliente httpx asíncrono inyectado desde el Composition Root.
        """
        self._base_url = base_url.rstrip("/")
        self._http_client = http_client

    async def buscar_por_lenguaje_natural(
        self, query: str, limite: int = 5
    ) -> list[DocumentoPatrimonial]:
        """
        Consulta el endpoint de búsqueda de AtoM y mapea los resultados
        al modelo de dominio mediante el Anti-Corruption Layer.
        """
        try:
            res = await self._http_client.get(
                f"{self._base_url}/api/informationobjects",
                params={"sq0": query, "limit": limite, "sf0": ""}
            )
            res.raise_for_status()
            data = res.json()

            resultados = data.get("results", [])
            documentos = []
            for idx, item in enumerate(resultados[:limite]):
                doc = self._mapear_desde_atom(item)
                doc.relevancia = round(1.0 - (idx * 0.1), 2)
                documentos.append(doc)

            return documentos

        except Exception as error:
            print(f"[AtoMHttpAdapter] Error en búsqueda: {error}")
            return []

    async def obtener_documento_por_codigo(
        self, codigo: str
    ) -> Optional[DocumentoPatrimonial]:
        """
        Obtiene un documento individual por su slug o código de referencia.
        """
        try:
            res = await self._http_client.get(
                f"{self._base_url}/api/informationobjects/{codigo}"
            )
            res.raise_for_status()
            return self._mapear_desde_atom(res.json())

        except httpx.HTTPStatusError as error:
            if error.response.status_code == 404:
                return None
            raise
        except Exception as error:
            print(f"[AtoMHttpAdapter] Error obteniendo documento '{codigo}': {error}")
            return None

    @staticmethod
    def _mapear_desde_atom(data: dict) -> DocumentoPatrimonial:
        """
        Anti-Corruption Layer: transforma el JSON con esquema Dublin Core
        de AtoM hacia la entidad de dominio DocumentoPatrimonial.

        Centraliza toda la lógica de mapeo en un único punto para facilitar
        el mantenimiento ante cambios en la API externa.
        """
        # Extraer código de referencia desde dc:identifier
        identificadores = data.get("dc:identifier", data.get("reference_code", []))
        if isinstance(identificadores, list):
            codigo_ref = next(
                (i for i in identificadores if not i.startswith("http")), ""
            )
        else:
            codigo_ref = str(identificadores)

        # Extraer slug y construir URL permanente
        slug = data.get("slug", "")
        href = data.get("href", data.get("url", ""))
        if not slug and href:
            slug = href.rstrip("/").split("/")[-1]
        url_sistema = href or f"https://archivopatrimonial.uahurtado.cl/index.php/{slug}"

        # Construir objetos digitales desde la miniatura
        objetos: list[ObjetoDigital] = []
        thumbnail = data.get("thumbnail", data.get("digital_object", {}).get("thumbnail"))
        if thumbnail:
            objetos.append(ObjetoDigital(
                url=thumbnail,
                tipo_mime=TipoMIME.IMAGE_JPEG,
                etiqueta="Miniatura"
            ))

        return DocumentoPatrimonial(
            id=str(data.get("id", slug)),
            codigo_referencia=codigo_ref,
            titulo=data.get("title", data.get("dc:title", "Sin título")),
            anio=data.get("dates", data.get("dc:date")),
            url_sistema=url_sistema,
            alcance_y_contenido=data.get("scope_and_content", data.get("description", "")),
            creadores=data.get("dc:creator", []),
            materias=data.get("dc:subject", []),
            cobertura=data.get("dc:coverage", []),
            objetos_digitales=objetos,
        )
