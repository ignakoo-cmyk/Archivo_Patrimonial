"""
Chat Context — Servicio de Dominio: ChatOrchestratorService
=============================================================
El orquestador central del Bounded Context de Chat.

Este es el corazón inteligente del sistema: NO es un simple pasamanos.
Contiene reglas de negocio ricas que definen el comportamiento académico
del asistente del Archivo Patrimonial UAH:

  1. evaluar_intencion_usuario()        → decide si el mensaje requiere RAG.
  2. validar_restricciones_academicas() → aplica anti-alucinación y rigor histórico.
  3. ensamblar_respuesta_con_citas()    → exige citas cuando se usan documentos.
  4. construir_prompt_contextualizado() → ensambla el prompt con el contexto RAG.

REGLA DE ORO: Opera exclusivamente con abstracciones (Puertos).
No conoce google.generativeai, httpx ni ninguna librería de infraestructura.
El System Prompt se inyecta como PromptTemplate, no está hardcodeado aquí.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from Dominio.objetos_de_valor.chat import (
    IntencionUsuario,
    Mensaje,
    PromptContextualizado,
    RolMensaje,
)
from Dominio.objetos_de_valor.prompt_template import PromptTemplate, PROMPT_ACADEMICO_UAH
from Dominio.entidades.sesion_chat import SesionChat
from Dominio.puertos.puertos_salida import ModeloLenguajePort, ServicioBusquedaPort
from Dominio.entidades.documento_patrimonial import DocumentoPatrimonial


# ─────────────────────────────────────────────────────────────
# Vocabulario de Intención — parte del conocimiento del dominio
# ─────────────────────────────────────────────────────────────

_TERMINOS_SALUDO: frozenset[str] = frozenset({
    "hola", "buenos días", "buenas tardes", "buenas noches", "buenas",
    "saludos", "qué tal", "cómo estás", "buen día", "hey", "hi",
    "quién eres", "presentate", "qué puedes hacer", "ayuda", "help",
})

_TERMINOS_ARCHIVO: frozenset[str] = frozenset({
    "archivo", "documento", "fondo", "colección", "coleccion", "fotografía",
    "foto", "fotos", "fotografías", "historia", "histórico", "historico",
    "uah", "hurtado", "patrimonial", "patrimonio", "jesuita", "jesuitas",
    "derechos", "humanos", "memoria", "catalogación", "atom", "expediente",
    "registro", "grabación", "audiovisual", "acervo", "siglo", "década",
    "año", "período", "época", "universidad", "alberto", "institucional",
    "serie", "subserie", "unidad", "legajo", "catalogar", "inventario",
    "catálogo", "catalogo", "repositorio", "fondo documental", "acta",
    "publicación", "publicacion", "revista", "carta", "correspondencia",
    "manuscrito", "impreso", "mapa", "plano", "dibujo", "imagen",
    "película", "video", "entrevista", "testimonio", "oral",
    "informe", "resolución", "decreto", "contrato", "reglamento",
    "santiago", "chile", "latinoamerica", "social", "educación", "iglesia",
    "buscar", "encontrar", "mostrar", "listar", "qué", "cuáles",
})

_INDICADORES_FUERA_AMBITO: frozenset[str] = frozenset({
    "receta", "cocina", "fútbol", "deporte", "clima", "tiempo",
    "política", "economía", "música", "película", "videojuego",
    "programar", "código", "python", "javascript",
})


@dataclass
class ChatOrchestratorService:
    """
    Servicio de Dominio principal del Chat Context.

    Orquesta el flujo completo de un mensaje: evalúa la intención,
    recupera contexto RAG si es necesario, construye el prompt y
    aplica validaciones de rigor académico antes de retornar la respuesta.

    Dependencias inyectadas (todas son abstracciones — Ports):
      - modelo_lenguaje:    ModeloLenguajePort (Gemini, OpenAI, etc.)
      - servicio_busqueda:  ServicioBusquedaPort (HTTP, mock, etc.)
      - prompt_template:    PromptTemplate (institucional, A/B test, etc.)
    """
    modelo_lenguaje: ModeloLenguajePort
    servicio_busqueda: ServicioBusquedaPort
    prompt_template: PromptTemplate = PROMPT_ACADEMICO_UAH

    # ──────────────────────────────────────────────────────────
    # Método principal de orquestación
    # ──────────────────────────────────────────────────────────

    async def procesar_mensaje(
        self, sesion: SesionChat, texto_usuario: str
    ) -> tuple[str, list[DocumentoPatrimonial], list[dict[str, str]]]:
        """
        Flujo completo de procesamiento de un mensaje de usuario.

        Pasos:
        1. Registrar el mensaje en la sesión.
        2. Evaluar la intención semántica del mensaje.
        3. Recuperar documentos del archivo si la intención lo requiere (RAG).
        4. Construir el prompt contextualizado.
        5. Llamar al LLM y obtener la respuesta cruda.
        6. Aplicar validaciones de restricciones académicas.
        7. Ensamblar la respuesta final con citas si corresponde.
        8. Extraer sugerencias dinámicas.
        9. Registrar la respuesta del asistente en la sesión.

        Returns:
        	Una tupla con:
        	  - Texto de respuesta final formateado en Markdown.
        	  - Lista de documentos recuperados de contexto.
        	  - Lista de sugerencias (quick replies).
        """
        # Paso 1: Registrar en historial
        sesion.agregar_mensaje(RolMensaje.USUARIO, texto_usuario)

        # Paso 2: Evaluar intención
        intencion = self.evaluar_intencion_usuario(texto_usuario)

        # Paso 3: Recuperar documentos RAG (solo si la intención lo requiere)
        documentos_contexto: list[DocumentoPatrimonial] = []
        total_corpus = 0
        facetas: dict[str, list[str]] = {}

        if intencion == IntencionUsuario.BUSQUEDA_ARCHIVO:
            documentos_contexto, total_corpus, facetas = await self.servicio_busqueda.buscar_documentos_relevantes(
                consulta=texto_usuario, limite=8
            )

        # ── INTERCEPCIÓN BÚSQUEDA FACETADA CONVERSACIONAL ──
        # Si el search-service devolvió facetas, significa que la búsqueda era
        # demasiado amplia (>20 docs) y se activó el pre-filtrado por metadatos.
        if facetas and (facetas.get("materias") or facetas.get("lugares")):
            sugerencias = []

            for materia in facetas.get("materias", []):
                sugerencias.append({
                    "label": materia.capitalize(),
                    "value": f"{texto_usuario} {materia}"
                })

            for lugar in facetas.get("lugares", []):
                sugerencias.append({
                    "label": lugar.capitalize(),
                    "value": f"{texto_usuario} {lugar}"
                })

            respuesta_intercep = (
                f"He encontrado **{total_corpus}** documentos relacionados con tu búsqueda. "
                f"Para ser más preciso y darte mejores resultados, ¿te interesa explorar "
                f"alguna de estas categorías específicas?"
            )

            sesion.agregar_mensaje(RolMensaje.ASISTENTE, respuesta_intercep)
            return respuesta_intercep, documentos_contexto, sugerencias[:5]
        # ───────────────────────────────────────────────────

        # Paso 4: Construir prompt
        prompt = self.construir_prompt_contextualizado(texto_usuario, documentos_contexto)

        # Paso 5: Llamar al LLM
        if self.modelo_lenguaje.esta_disponible():
            respuesta_cruda = await self.modelo_lenguaje.generar_respuesta(prompt)
        else:
            respuesta_cruda = self._respuesta_fallback_sin_llm(documentos_contexto)

        # Paso 6: Validar restricciones académicas
        respuesta_validada = self.validar_restricciones_academicas(
            respuesta_cruda, documentos_contexto
        )

        # Paso 7: Extraer sugerencias dinámicas (antes de agregar las citas)
        sugerencias = []
        respuesta_sin_sug = respuesta_validada
        if "SUGERENCIAS:" in respuesta_sin_sug:
            partes = respuesta_sin_sug.split("SUGERENCIAS:")
            respuesta_sin_sug = partes[0].strip()
            bloque_sug = partes[1].strip()
            for linea in bloque_sug.split('\n'):
                if linea.strip().startswith('-'):
                    sug_texto = linea.strip()[1:].strip().replace('*', '')
                    if sug_texto:
                        sugerencias.append({"label": sug_texto, "value": sug_texto})
            sugerencias = sugerencias[:3]

        # Paso 8: Ensamblar con citas obligatorias
        respuesta_final = self.ensamblar_respuesta_con_citas(
            respuesta_sin_sug, documentos_contexto
        )

        # Paso 9: Registrar respuesta en sesión
        sesion.agregar_mensaje(RolMensaje.ASISTENTE, respuesta_final)

        return respuesta_final, documentos_contexto, sugerencias

    # ──────────────────────────────────────────────────────────
    # Reglas de Negocio Ricas del Dominio
    # ──────────────────────────────────────────────────────────

    def evaluar_intencion_usuario(self, texto: str) -> IntencionUsuario:
        """
        REGLA DE NEGOCIO: Determina la intención semántica del mensaje.

        Implementa un clasificador léxico de dominio que:
        1. Detecta saludos y preguntas generales → no requieren RAG.
        2. Detecta términos del dominio archivístico → requieren búsqueda RAG.
        3. Detecta temas completamente ajenos → retorna fuera de ámbito.

        Esta lógica vive en el dominio porque es una REGLA DE NEGOCIO:
        define qué tipo de consultas son válidas para este asistente,
        independientemente de qué LLM o servicio de búsqueda se use.

        Returns:
            IntencionUsuario clasificando el tipo de consulta.
        """
        texto_lower = texto.strip().lower()
        palabras = set(re.findall(r'\b\w+\b', texto_lower))

        if palabras & _TERMINOS_SALUDO and not (palabras & _TERMINOS_ARCHIVO):
            return IntencionUsuario.SALUDO_O_GENERAL
        if len(texto_lower) < 8 and not (palabras & _TERMINOS_ARCHIVO):
            return IntencionUsuario.SALUDO_O_GENERAL

        indicadores_fuera = palabras & _INDICADORES_FUERA_AMBITO
        indicadores_archivo = palabras & _TERMINOS_ARCHIVO
        if indicadores_fuera and not indicadores_archivo:
            return IntencionUsuario.FUERA_DE_AMBITO

        if indicadores_archivo:
            return IntencionUsuario.BUSQUEDA_ARCHIVO

        return IntencionUsuario.BUSQUEDA_ARCHIVO

    def validar_restricciones_academicas(
        self, respuesta: str, documentos_usados: list[DocumentoPatrimonial]
    ) -> str:
        """
        REGLA DE NEGOCIO: Aplica validaciones de rigor histórico y anti-alucinación.

        Verifica que la respuesta del LLM cumpla con las políticas académicas
        del Archivo Patrimonial UAH:

        1. Si el LLM genera una respuesta muy corta con documentos disponibles,
           añade una nota de contexto para guiar al usuario.
        2. Detecta posibles alucinaciones: si la respuesta menciona URLs del
           catálogo que no estaban en el contexto provisto, agrega advertencia.
        3. Normaliza el tono (actualmente placeholder para lógica más compleja).

        Args:
            respuesta:        Texto crudo generado por el LLM.
            documentos_usados: Documentos inyectados como contexto al LLM.

        Returns:
            Respuesta validada, posiblemente con anotaciones de advertencia.
        """
        if not respuesta or not respuesta.strip():
            return (
                "Lo siento, no pude generar una respuesta en este momento. "
                "Por favor, intenta reformular tu pregunta."
            )

        # Regla de completitud mínima
        if documentos_usados and len(respuesta.strip()) < 50:
            respuesta += (
                "\n\n> *Nota: La búsqueda encontró documentos relevantes. "
                "Considera reformular tu pregunta para obtener más detalles.*"
            )

        # Regla anti-alucinación: verificar URLs inventadas
        urls_en_respuesta = re.findall(
            r'https?://archivopatrimonial\.uahurtado\.cl/\S+', respuesta
        )
        urls_contexto = {doc.url_catalogo for doc in documentos_usados if doc.tiene_url}
        urls_inventadas = [u for u in urls_en_respuesta if u not in urls_contexto]

        if urls_inventadas:
            respuesta += (
                "\n\n> *Advertencia de rigor académico: Algunas URLs en esta "
                "respuesta pueden no estar verificadas. Consulta el catálogo oficial.*"
            )

        return respuesta

    def ensamblar_respuesta_con_citas(
        self, respuesta: str, documentos_usados: list[DocumentoPatrimonial]
    ) -> str:
        """
        REGLA DE NEGOCIO: Si se usaron documentos del archivo, DEBE haber citas.

        Esta es una invariante del dominio académico: el asistente del Archivo
        Patrimonial debe siempre citar sus fuentes cuando las usa. Esta regla
        garantiza transparencia y rigor histórico.

        Si la respuesta no incluye ya referencias a los documentos usados,
        este método las añade automáticamente como sección de fuentes.

        Args:
            respuesta:        Texto ya validado del LLM.
            documentos_usados: Documentos que formaron el contexto RAG.

        Returns:
            Respuesta final con sección de fuentes si corresponde.
        """
        if not documentos_usados:
            return respuesta

        documentos_con_url = [doc for doc in documentos_usados if doc.tiene_url]
        if not documentos_con_url:
            return respuesta

        urls_ya_citadas = any(
            doc.url_catalogo in respuesta for doc in documentos_con_url
        )

        if urls_ya_citadas:
            return respuesta

        lineas_citas = ["\n\n---\n**📚 Fuentes del Archivo Patrimonial UAH:**\n"]
        for i, doc in enumerate(documentos_con_url, start=1):
            anio_str = f" ({doc.anio})" if doc.anio else ""
            lineas_citas.append(
                f"{i}. [{doc.titulo}{anio_str}]({doc.url_catalogo})"
            )

        return respuesta + "\n".join(lineas_citas)

    def construir_prompt_contextualizado(
        self, consulta: str, documentos: list[DocumentoPatrimonial]
    ) -> PromptContextualizado:
        """
        Construye el PromptContextualizado inyectando el contexto RAG.

        Delega el ensamblado del texto final al PromptTemplate inyectado,
        manteniendo el dominio desacoplado del contenido específico del prompt.

        Args:
            consulta:    Texto original del usuario.
            documentos:  Documentos recuperados del archivo para contexto.

        Returns:
            PromptContextualizado listo para ser enviado al ModeloLenguajePort.
        """
        if documentos:
            partes_contexto = [
                f"--- DOCUMENTO {i} (Relevancia: {doc.puntuacion_relevancia:.3f}) ---\n"
                f"{doc.resumen_para_prompt}"
                for i, doc in enumerate(documentos, start=1)
            ]
            bloque_contexto = (
                f"\n\n═══ CONTEXTO: DOCUMENTOS DEL ARCHIVO PATRIMONIAL ═══\n"
                f"Búsqueda realizada: \"{consulta}\"\n"
                f"Documentos encontrados: {len(documentos)}\n\n"
                + "\n\n".join(partes_contexto)
            )
        else:
            bloque_contexto = (
                "\n\n═══ CONTEXTO ═══\n"
                "No se encontraron documentos relevantes en el archivo para esta consulta."
            )

        texto_completo = self.prompt_template.construir_prompt_completo(
            consulta=consulta,
            bloque_contexto=bloque_contexto,
        )

        return PromptContextualizado(
            texto_completo=texto_completo,
            n_documentos_contexto=len(documentos),
            requirio_busqueda=len(documentos) > 0,
        )

    # ──────────────────────────────────────────────────────────
    # Métodos privados auxiliares
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _respuesta_fallback_sin_llm(documentos: list[DocumentoPatrimonial]) -> str:
        """Respuesta de modo degradado cuando el LLM no está disponible."""
        if not documentos:
            return (
                "*Modo sin IA activo.* No se encontraron documentos relevantes. "
                "Configura `GEMINI_API_KEY` para habilitar respuestas con IA."
            )
        titulos = ", ".join(f"*{doc.titulo}*" for doc in documentos[:3])
        return (
            f"*Modo sin IA activo.* Documentos encontrados: {titulos}. "
            f"Configura `GEMINI_API_KEY` para obtener respuestas inteligentes."
        )
