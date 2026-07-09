"""
Capa de Aplicación — Caso de Uso: BuscadorDocumentosUseCase
============================================================
Implementa el Puerto de Entrada PuertoBuscadorDocumentos.

Actúa como capa de coordinación entre el controlador HTTP y el dominio.
Este es el lugar correcto para añadir capas transversales (cross-cutting concerns)
sin contaminar la lógica pura del dominio:
  - Registro de auditoría (logs de quién buscó qué y cuándo)
  - Caché de resultados para consultas frecuentes (Redis)
  - Métricas de latencia y telemetría (OpenTelemetry)

REGLA: No contiene reglas de negocio puras; esas viven en el Dominio.
Solo coordina el flujo: recibe una intención → consulta el puerto de salida
→ estructura la respuesta en el formato esperado por la Presentación.
"""

from __future__ import annotations

from typing import Optional

from Aplicacion.puertos.entrada import PuertoBuscadorDocumentos
from Dominio.entidades.documento_patrimonial import DocumentoPatrimonial
from Dominio.puertos.puerto_archivo_patrimonial import PuertoArchivoPatrimonial


class BuscadorDocumentosUseCase(PuertoBuscadorDocumentos):
    """
    Implementación concreta del Puerto de Entrada PuertoBuscadorDocumentos.

    Recibe el PuertoArchivoPatrimonial inyectado (Dependency Inversion),
    lo que permite que el controlador HTTP desconozca si la fuente de datos
    es AtoM real, un JSON local, o un Mock de desarrollo.
    """

    def __init__(self, repositorio: PuertoArchivoPatrimonial) -> None:
        """
        Args:
            repositorio: Puerto de salida que abstrae el acceso a la fuente
                         de datos del Archivo Patrimonial. Puede ser:
                         - AtoMHttpAdapter (producción)
                         - MockAtoMAdapter (desarrollo/tests)
        """
        self._repositorio = repositorio

    async def ejecutar_busqueda(self, query: str, limite: int = 5) -> dict:
        """
        Punto de entrada principal para consultas en lenguaje natural.
        Retorna un diccionario serializable listo para ser enviado como respuesta HTTP.
        """
        documentos = await self._repositorio.buscar_por_lenguaje_natural(query, limite=limite)

        rich_cards = [self._documento_a_rich_card(doc) for doc in documentos]
        quick_replies = self._generar_quick_replies(query, documentos)

        if documentos:
            mensaje = (
                f"Se encontraron {len(documentos)} registros relevantes "
                f"para la consulta '{query}'. A continuación se presentan "
                f"los documentos ordenados por relevancia."
            )
        else:
            mensaje = (
                f"No se encontraron documentos que coincidan con '{query}'. "
                f"Se sugiere reformular la consulta utilizando términos más amplios "
                f"o explorar las categorías temáticas disponibles."
            )

        return {
            "mensaje": mensaje,
            "documentos": [_documento_a_dict(doc) for doc in documentos],
            "rich_cards": rich_cards,
            "quick_replies": quick_replies,
            "total": len(documentos),
        }

    async def obtener_detalle(self, codigo: str) -> dict:
        """
        Obtiene el detalle de un documento específico por código de referencia.
        Pensado para cuando el usuario hace clic en una Rich Card y quiere
        profundizar en un registro particular.
        """
        documento = await self._repositorio.obtener_documento_por_codigo(codigo)

        if not documento:
            return {
                "mensaje": f"No se encontró un documento con el código '{codigo}'.",
                "documento": None,
                "quick_replies": [
                    {"label": "Buscar por otro código", "value": "buscar código"},
                    {"label": "Ver categorías", "value": "categorías"},
                ],
            }

        card = self._documento_a_rich_card(documento)

        return {
            "mensaje": f"Documento encontrado: {documento.titulo}.",
            "documento": _documento_a_dict(documento),
            "rich_card": card,
            "quick_replies": [
                {"label": "Ver documentos similares", "value": f"similares a {documento.titulo}"},
                {"label": "Nueva búsqueda", "value": "inicio"},
            ],
        }

    # ── Métodos privados de ensamblado de presentación ──────────────────────

    @staticmethod
    def _documento_a_rich_card(doc: DocumentoPatrimonial) -> dict:
        """
        Transforma una entidad de dominio en una estructura de Rich Card
        consumible directamente por el componente de UI del frontend.

        Esta lógica de presentación vive en Aplicación (no en Dominio)
        porque depende del formato esperado por el frontend.
        """
        miniatura_url: Optional[str] = None
        if doc.miniatura:
            miniatura_url = doc.miniatura.url

        return {
            "id": doc.id,
            "titulo": doc.titulo,
            "codigo_referencia": doc.codigo_referencia,
            "anio": doc.anio,
            "url": doc.url_sistema,
            "descripcion_corta": doc.descripcion_corta,
            "materias": doc.materias[:4],
            "miniatura_url": miniatura_url,
            "relevancia": round(doc.relevancia, 2),
        }

    @staticmethod
    def _generar_quick_replies(query: str, documentos: list[DocumentoPatrimonial]) -> list[dict]:
        """
        Genera sugerencias contextuales basadas en los resultados obtenidos.
        Estas se renderizarán como botones de acción rápida en el frontend.
        """
        replies = []

        todas_materias: list[str] = []
        for doc in documentos:
            todas_materias.extend(doc.materias)

        materias_unicas = list(dict.fromkeys(todas_materias))[:3]

        for materia in materias_unicas:
            replies.append({"label": f"Explorar: {materia}", "value": materia})

        if not replies:
            replies = [
                {"label": "Ver fondos documentales", "value": "fondos"},
                {"label": "Buscar por fecha", "value": "documentos por fecha"},
                {"label": "Ayuda", "value": "ayuda"},
            ]

        return replies


def _documento_a_dict(doc: DocumentoPatrimonial) -> dict:
    """
    Serializa un DocumentoPatrimonial (@dataclass) a dict para la respuesta HTTP.
    Reemplaza model_dump() de Pydantic ahora que el Dominio usa @dataclass puro.
    Centraliza toda la lógica de serialización en la capa de Aplicación.
    """
    return {
        "id": doc.id,
        "codigo_referencia": doc.codigo_referencia,
        "titulo": doc.titulo,
        "anio": doc.anio,
        "url_sistema": doc.url_sistema,
        "alcance_y_contenido": doc.alcance_y_contenido,
        "creadores": doc.creadores,
        "materias": doc.materias,
        "cobertura": doc.cobertura,
        "objetos_digitales": [
            {"url": o.url, "tipo_mime": o.tipo_mime.value, "etiqueta": o.etiqueta}
            for o in doc.objetos_digitales
        ],
        "relevancia": doc.relevancia,
    }
