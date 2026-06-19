"""
Chat Context — Servicio de Dominio: ChatOrchestratorService
=============================================================
El orquestador central del Bounded Context de Chat.

Este es el corazón inteligente del sistema: NO es un simple pasamanos.
Contiene reglas de negocio ricas que definen el comportamiento académico
del asistente del Archivo Patrimonial UAH:

  1. evaluar_intencion_usuario()    → decide si el mensaje requiere RAG.
  2. validar_restricciones_academicas() → aplica anti-alucinación y rigor histórico.
  3. ensamblar_respuesta_con_citas() → exige citas cuando se usan documentos.
  4. construir_prompt_contextualizado() → ensambla el prompt con el contexto RAG.

REGLA DE ORO: Opera exclusivamente con abstracciones (Puertos).
No conoce google.generativeai, httpx ni ninguna librería de infraestructura.
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
    "archivo", "documento", "fondo", "colección", "fotografía", "foto",
    "historia", "histórico", "uah", "hurtado", "patrimonial", "patrimonio",
    "jesuita", "derechos humanos", "memoria", "catalogación", "atom",
    "expediente", "registro", "grabación", "audiovisual", "acervo",
    "siglo", "década", "año", "período", "época", "universidad",
})

_INDICADORES_FUERA_AMBITO: frozenset[str] = frozenset({
    "receta", "cocina", "fútbol", "deporte", "clima", "tiempo",
    "política", "economía", "música", "película", "videojuego",
    "programar", "código", "python", "javascript",
})

# System Prompt institucional — conocimiento de negocio del dominio académico
_SYSTEM_PROMPT_ACADEMICO = """Eres el Asistente Digital del Archivo Patrimonial de la \
Universidad Alberto Hurtado (UAH).

TU PERSONALIDAD:
- Eres profesional, directo, amable y conciso. Hablas con un tono académico pero conversacional.
- Actúas como un bibliotecario experto. NUNCA menciones que eres una Inteligencia Artificial, un modelo de lenguaje, o que estás leyendo un "contexto" o "documentos proporcionados". Simplemente entrega la información como si la supieras.

REGLAS DE INTERACCIÓN:
1. Si el usuario saluda, devuélvele el saludo de forma breve y ofrécele ayuda directamente (ej. "¡Hola! Bienvenido al Archivo Patrimonial UAH. ¿Qué documento o tema histórico buscas hoy?"). NO repitas el resumen de lo que hace el archivo a menos que te pregunten específicamente "¿Qué es este archivo?".
2. Si la respuesta está en la información que se te entrega, respóndela de forma directa y natural. Al final, cita el título del documento y su URL si está disponible.
3. Si la respuesta NO está en la información, di amablemente que no tienes esa información en el Archivo Patrimonial.
4. NUNCA inventes información que no posees ni enlaces a páginas externas.
5. Usa formato Markdown para estructurar tus respuestas. Sé conciso pero informativo.
"""


@dataclass
class ChatOrchestratorService:
    """
    Servicio de Dominio principal del Chat Context.

    Orquesta el flujo completo de un mensaje: evalúa la intención,
    recupera contexto RAG si es necesario, construye el prompt y
    aplica validaciones de rigor académico antes de retornar la respuesta.
    """
    modelo_lenguaje: ModeloLenguajePort
    servicio_busqueda: ServicioBusquedaPort

    # ──────────────────────────────────────────────────────────
    # Método principal de orquestación
    # ──────────────────────────────────────────────────────────

    async def procesar_mensaje(self, sesion: SesionChat, texto_usuario: str) -> tuple[str, list[DocumentoPatrimonial]]:
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
        8. Registrar la respuesta del asistente en la sesión.

        Returns:
        	Una tupla con:
        	  - Texto de respuesta final formateado en Markdown.
        	  - Lista de documentos recuperados de contexto.
        """
        # Paso 1: Registrar en historial
        sesion.agregar_mensaje(RolMensaje.USUARIO, texto_usuario)

        # Paso 2: Evaluar intención
        intencion = self.evaluar_intencion_usuario(texto_usuario)

        # Paso 3: Recuperar documentos RAG (solo si la intención lo requiere)
        documentos_contexto: list[DocumentoPatrimonial] = []
        if intencion == IntencionUsuario.BUSQUEDA_ARCHIVO:
            documentos_contexto = await self.servicio_busqueda.buscar_documentos_relevantes(
                consulta=texto_usuario, limite=5
            )

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

        # Paso 7: Ensamblar con citas obligatorias
        respuesta_final = self.ensamblar_respuesta_con_citas(
            respuesta_validada, documentos_contexto
        )

        # Paso 8: Registrar respuesta en sesión
        sesion.agregar_mensaje(RolMensaje.ASISTENTE, respuesta_final)

        return respuesta_final, documentos_contexto

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

        # Prioridad 1: Saludos y consultas de presentación
        if palabras & _TERMINOS_SALUDO or len(texto_lower) < 15:
            return IntencionUsuario.SALUDO_O_GENERAL

        # Prioridad 2: Temas fuera del ámbito del archivo
        indicadores_fuera = palabras & _INDICADORES_FUERA_AMBITO
        indicadores_archivo = palabras & _TERMINOS_ARCHIVO
        if indicadores_fuera and not indicadores_archivo:
            return IntencionUsuario.FUERA_DE_AMBITO

        # Prioridad 3: Consulta sobre el archivo patrimonial
        if indicadores_archivo:
            return IntencionUsuario.BUSQUEDA_ARCHIVO

        # Por defecto: tratar como búsqueda (es mejor preguntar que omitir)
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
        2. Detecta posibles alucinaciones: si la respuesta menciona documentos
           con nombres que no están en el contexto provisto, agrega advertencia.
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

        # Regla de completitud mínima: respuesta demasiado corta con contexto disponible
        if documentos_usados and len(respuesta.strip()) < 50:
            respuesta += (
                "\n\n> *Nota: La búsqueda encontró documentos relevantes. "
                "Considera reformular tu pregunta para obtener más detalles.*"
            )

        # Regla anti-alucinación: verificar si el LLM inventó URLs no provistas
        titulos_contexto = {doc.titulo.lower() for doc in documentos_usados}
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

        # Verificar si la respuesta ya incluye citas de los documentos
        documentos_con_url = [doc for doc in documentos_usados if doc.tiene_url]
        if not documentos_con_url:
            return respuesta

        # Detectar si ya hay citas en la respuesta (URLs del catálogo)
        urls_ya_citadas = any(
            doc.url_catalogo in respuesta for doc in documentos_con_url
        )

        if urls_ya_citadas:
            return respuesta

        # Ensamblar sección de fuentes obligatoria
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

        Separa la lógica de construcción del prompt (dominio) del envío real
        al LLM (adaptador). El prompt resultante sigue la estructura:
          [System Prompt] + [Contexto RAG] + [Pregunta del usuario]

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

        texto_completo = (
            f"{_SYSTEM_PROMPT_ACADEMICO}"
            f"{bloque_contexto}"
            f"\n\n═══ PREGUNTA DEL USUARIO ═══\n{consulta}\n\n"
            "Responde de forma útil basándote en los documentos anteriores. "
            "Si no hay documentos relevantes, dilo honestamente y sugiere términos alternativos."
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
