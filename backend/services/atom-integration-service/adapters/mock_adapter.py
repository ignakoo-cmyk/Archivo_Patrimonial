"""
Adaptador Mock -- Para Desarrollo sin AtoM
=============================================
Implementa PuertoArchivoPatrimonial con datos ficticios para permitir al
equipo de frontend maquetar la UI interactiva (Rich Cards, Quick Replies)
sin necesidad de credenciales ni conexion al sistema AtoM real.

Uso:
    En main.py, reemplazar la inyeccion del adapter real por este mock:

        # Produccion (requiere AtoM accesible)
        # app.state.use_case = BuscadorDocumentosUseCase(
        #     AtoMHttpAdapter(base_url=ATOM_BASE_URL, http_client=http_client)
        # )

        # Desarrollo (sin dependencias externas)
        from adapters.mock_adapter import MockAtoMAdapter
        app.state.use_case = BuscadorDocumentosUseCase(MockAtoMAdapter())
"""

from typing import Optional
from domain.models import DocumentoPatrimonial, ObjetoDigital, TipoMIME
from application.ports import PuertoArchivoPatrimonial


# Corpus de documentos ficticios representativos del Archivo Patrimonial UAH
_MOCK_DOCUMENTS = [
    DocumentoPatrimonial(
        id="mock-001",
        codigo_referencia="UAH-D-1027",
        titulo="Informe sobre detenidos desaparecidos en la zona norte, 1975",
        anio="1975",
        url_sistema="https://archivopatrimonial.uahurtado.cl/index.php/informe-detenidos-norte",
        alcance_y_contenido=(
            "Documento mecanografiado de 23 paginas que registra testimonios "
            "recopilados por la Vicaria de la Solidaridad relativos a casos de "
            "detencion y desaparicion forzada en las provincias de Antofagasta "
            "e Iquique durante el periodo 1973-1975. Incluye fichas individuales "
            "con datos biograficos, circunstancias de la detencion y estado de "
            "las gestiones judiciales."
        ),
        creadores=["Vicaria de la Solidaridad"],
        materias=["Derechos Humanos", "Detenidos desaparecidos", "Chile -- Historia"],
        cobertura=["Antofagasta (Chile)", "Iquique (Chile)"],
        objetos_digitales=[
            ObjetoDigital(
                url="https://archivopatrimonial.uahurtado.cl/uploads/thumb_001.jpg",
                tipo_mime=TipoMIME.IMAGE_JPEG,
                etiqueta="Portada del informe"
            )
        ],
    ),
    DocumentoPatrimonial(
        id="mock-002",
        codigo_referencia="UAH-F-0412",
        titulo="Registro fotografico de la Poblacion La Victoria, 1984",
        anio="1984",
        url_sistema="https://archivopatrimonial.uahurtado.cl/index.php/fotos-la-victoria",
        alcance_y_contenido=(
            "Serie de 47 fotografias en blanco y negro que documentan la vida "
            "cotidiana, actividades comunitarias y operativos militares en la "
            "Poblacion La Victoria durante 1984. Fotografo: Luis Navarro."
        ),
        creadores=["Navarro, Luis"],
        materias=["Fotografias", "Poblaciones (Chile)", "Movimientos sociales"],
        cobertura=["Santiago (Chile: Ciudad)"],
        objetos_digitales=[
            ObjetoDigital(
                url="https://archivopatrimonial.uahurtado.cl/uploads/thumb_002.jpg",
                tipo_mime=TipoMIME.IMAGE_JPEG,
                etiqueta="Foto representativa de la serie"
            )
        ],
    ),
    DocumentoPatrimonial(
        id="mock-003",
        codigo_referencia="UAH-A-0088",
        titulo="Grabacion de audio: Homilia del Cardenal Silva Henriquez, 1976",
        anio="1976",
        url_sistema="https://archivopatrimonial.uahurtado.cl/index.php/homilia-silva-henriquez",
        alcance_y_contenido=(
            "Grabacion en cinta magnetica (35 minutos) de la homilia pronunciada "
            "por el Cardenal Raul Silva Henriquez en la Catedral de Santiago el "
            "18 de septiembre de 1976, con referencias directas a la situacion "
            "de los derechos humanos en Chile."
        ),
        creadores=["Silva Henriquez, Raul"],
        materias=["Iglesia Catolica", "Derechos Humanos", "Homilias"],
        cobertura=["Santiago (Chile: Ciudad)"],
        objetos_digitales=[
            ObjetoDigital(
                url="https://archivopatrimonial.uahurtado.cl/uploads/audio_088.mp3",
                tipo_mime=TipoMIME.AUDIO_MPEG,
                etiqueta="Audio de la homilia"
            )
        ],
    ),
    DocumentoPatrimonial(
        id="mock-004",
        codigo_referencia="3-2-1-4",
        titulo="Y en que estan los profes?",
        anio="1983",
        url_sistema="https://archivopatrimonial.uahurtado.cl/index.php/y-en-que-estan-los-profes",
        alcance_y_contenido=(
            "Volante impreso distribuido en la Universidad de Chile durante 1983. "
            "Aborda la situacion laboral y gremial del profesorado universitario "
            "en el contexto de las reformas educacionales del regimen militar."
        ),
        creadores=["Basso, Patricio"],
        materias=["Profesores", "Educacion (Chile)", "Volantes", "Universidad de Chile"],
        cobertura=["Santiago (Chile: Ciudad)"],
    ),
]


class MockAtoMAdapter(PuertoArchivoPatrimonial):
    """
    Adaptador de desarrollo que retorna datos ficticios.
    Permite al equipo de frontend trabajar de forma autonoma con el contrato
    de datos completo mientras se gestiona el acceso a la API de AtoM.
    """

    async def buscar_por_lenguaje_natural(self, query: str, limite: int = 5) -> list[DocumentoPatrimonial]:
        query_lower = query.lower()
        resultados = []

        for doc in _MOCK_DOCUMENTS:
            texto_busqueda = f"{doc.titulo} {doc.alcance_y_contenido} {' '.join(doc.materias)}".lower()
            if any(palabra in texto_busqueda for palabra in query_lower.split()):
                doc_copia = doc.model_copy()
                doc_copia.relevancia = 0.85
                resultados.append(doc_copia)

        # Si no hay coincidencias, devolver todos para que el frontend siempre
        # tenga datos con los que trabajar durante el desarrollo
        if not resultados:
            resultados = [d.model_copy() for d in _MOCK_DOCUMENTS[:limite]]
            for r in resultados:
                r.relevancia = 0.5

        return resultados[:limite]

    async def obtener_documento_por_codigo(self, codigo: str) -> Optional[DocumentoPatrimonial]:
        for doc in _MOCK_DOCUMENTS:
            if doc.codigo_referencia == codigo or doc.id == codigo:
                return doc.model_copy()
        return None
