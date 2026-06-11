"""
Capa de Aplicacion -- Caso de Uso
====================================
Orquesta la logica de aplicacion. No contiene reglas de negocio puras (esas viven
en el Dominio), sino que coordina el flujo: recibe una intencion, consulta los puertos,
estructura la respuesta y la devuelve en un formato serializable para la capa de
presentacion (REST API, GraphQL, CLI, etc.).
"""

from typing import Optional
from domain.models import DocumentoPatrimonial
from application.ports import PuertoArchivoPatrimonial


class BuscadorDocumentosUseCase:
    """
    Application Service que encapsula la logica de busqueda y presentacion
    de documentos patrimoniales. Recibe el puerto inyectado (Dependency Inversion).
    """

    def __init__(self, repositorio: PuertoArchivoPatrimonial):
        self._repositorio = repositorio

    async def ejecutar_busqueda(self, query: str, limite: int = 5) -> dict:
        """
        Punto de entrada principal para consultas en lenguaje natural.
        Retorna un diccionario serializable listo para ser enviado como respuesta HTTP.
        """
        documentos = await self._repositorio.buscar_por_lenguaje_natural(query, limite=limite)

        # Construir Rich Cards para el frontend
        rich_cards = [self._documento_a_rich_card(doc) for doc in documentos]

        # Generar sugerencias de busqueda contextual
        quick_replies = self._generar_quick_replies(query, documentos)

        # Mensaje textual principal
        if documentos:
            mensaje = (
                f"Se encontraron {len(documentos)} registros relevantes "
                f"para la consulta '{query}'. A continuacion se presentan "
                f"los documentos ordenados por relevancia."
            )
        else:
            mensaje = (
                f"No se encontraron documentos que coincidan con '{query}'. "
                f"Se sugiere reformular la consulta utilizando terminos mas amplios "
                f"o explorar las categorias tematicas disponibles."
            )

        return {
            "mensaje": mensaje,
            "documentos": [doc.model_dump() for doc in documentos],
            "rich_cards": rich_cards,
            "quick_replies": quick_replies,
            "total": len(documentos),
        }

    async def obtener_detalle(self, codigo: str) -> dict:
        """
        Obtiene el detalle de un documento especifico por codigo de referencia.
        Pensado para cuando el usuario hace clic en una Rich Card y quiere
        profundizar en un registro particular.
        """
        documento = await self._repositorio.obtener_documento_por_codigo(codigo)

        if not documento:
            return {
                "mensaje": f"No se encontro un documento con el codigo '{codigo}'.",
                "documento": None,
                "quick_replies": [
                    {"label": "Buscar por otro codigo", "value": "buscar codigo"},
                    {"label": "Ver categorias", "value": "categorias"},
                ],
            }

        card = self._documento_a_rich_card(documento)

        return {
            "mensaje": f"Documento encontrado: {documento.titulo}.",
            "documento": documento.model_dump(),
            "rich_card": card,
            "quick_replies": [
                {"label": "Ver documentos similares", "value": f"similares a {documento.titulo}"},
                {"label": "Nueva busqueda", "value": "inicio"},
            ],
        }

    @staticmethod
    def _documento_a_rich_card(doc: DocumentoPatrimonial) -> dict:
        """
        Transforma una entidad de dominio en una estructura de Rich Card
        consumible directamente por el componente de UI del frontend.
        """
        # Seleccionar miniatura si existe
        miniatura_url: Optional[str] = None
        for obj in doc.objetos_digitales:
            if obj.tipo_mime.value.startswith("image/"):
                miniatura_url = obj.url
                break

        return {
            "id": doc.id,
            "titulo": doc.titulo,
            "codigo_referencia": doc.codigo_referencia,
            "anio": doc.anio,
            "url": doc.url_sistema,
            "descripcion_corta": (doc.alcance_y_contenido[:180] + "...") if len(doc.alcance_y_contenido) > 180 else doc.alcance_y_contenido,
            "materias": doc.materias[:4],
            "miniatura_url": miniatura_url,
            "relevancia": round(doc.relevancia, 2),
        }

    @staticmethod
    def _generar_quick_replies(query: str, documentos: list[DocumentoPatrimonial]) -> list[dict]:
        """
        Genera sugerencias contextuales basadas en los resultados obtenidos.
        Estas se renderizaran como botones de accion rapida en el frontend.
        """
        replies = []

        # Extraer materias frecuentes de los resultados para sugerir refinamiento
        todas_materias: list[str] = []
        for doc in documentos:
            todas_materias.extend(doc.materias)

        materias_unicas = list(dict.fromkeys(todas_materias))[:3]

        for materia in materias_unicas:
            replies.append({
                "label": f"Explorar: {materia}",
                "value": materia,
            })

        if not replies:
            replies = [
                {"label": "Ver fondos documentales", "value": "fondos"},
                {"label": "Buscar por fecha", "value": "documentos por fecha"},
                {"label": "Ayuda", "value": "ayuda"},
            ]

        return replies
