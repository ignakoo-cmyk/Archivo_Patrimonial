"""
Chat Context — Objeto de Valor: PromptTemplate
================================================
Encapsula el System Prompt institucional del Asistente Digital del
Archivo Patrimonial UAH como un Objeto de Valor del dominio.

Por qué vive en el Dominio (no en Infraestructura ni Aplicación):
  - El prompt ES una regla de negocio: define la personalidad, los límites
    de respuesta y el rigor académico del asistente.
  - Cambiar el prompt cambia el COMPORTAMIENTO del sistema, no solo
    la implementación técnica.
  - Se inyecta en ChatOrchestratorService como dependencia, permitiendo
    swappear prompts (ej. para A/B testing o diferentes contextos) sin
    tocar la lógica de orquestación.

REGLA DE ORO: Solo Python estándar. Sin imports de frameworks.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptTemplate:
    """
    Objeto de Valor inmutable que encapsula el System Prompt del asistente.

    Es frozen=True porque el template no debe modificarse en runtime.
    Cualquier variación de prompt debe ser una nueva instancia inyectada
    en el Composition Root.
    """
    system_prompt: str

    def __post_init__(self) -> None:
        if not self.system_prompt or not self.system_prompt.strip():
            raise ValueError("El PromptTemplate no puede tener un system prompt vacío.")

    def construir_prompt_completo(
        self, consulta: str, bloque_contexto: str
    ) -> str:
        """
        Ensambla el prompt final combinando el system prompt institucional,
        el contexto RAG recuperado y la pregunta del usuario.

        Args:
            consulta:        Texto original de la pregunta del usuario.
            bloque_contexto: Contexto RAG ya formateado (documentos o mensaje vacío).

        Returns:
            Texto completo del prompt listo para ser enviado al LLM.
        """
        return (
            f"{self.system_prompt}"
            f"{bloque_contexto}"
            f"\n\n═══ PREGUNTA DEL USUARIO ═══\n{consulta}\n\n"
            "Responde de forma útil basándote en los documentos anteriores. "
            "Si no hay documentos relevantes, dilo honestamente y sugiere términos alternativos."
        )


# ── Template de Producción ────────────────────────────────────────────────────
# Instancia del template institucional. Se inyecta desde el Composition Root
# en ChatOrchestratorService. Puede ser reemplazado por otro template en tests.

PROMPT_ACADEMICO_UAH = PromptTemplate(
    system_prompt="""Eres el Asistente Digital del Archivo Patrimonial de la \
Universidad Alberto Hurtado (UAH).

TU PERSONALIDAD Y DISEÑO VISUAL:
- Eres profesional, directo, amable y conciso. Hablas con un tono académico pero conversacional.
- NUNCA menciones que eres una Inteligencia Artificial o un modelo de lenguaje.
- ESTÉTICA VISUAL: Escribe **SIEMPRE** utilizando un formato rico en Markdown.
  * Usa **negritas** para resaltar conceptos clave, años o títulos importantes.
  * Usa viñetas (`- `) para estructurar ideas o listas.
  * Mantén los párrafos cortos y fáciles de leer.

REGLAS DE INTERACCIÓN:
1. Saludos: Si el usuario saluda o hace preguntas genéricas, responde amablemente y sugiere de inmediato 3 temas usando viñetas.
2. Recomendaciones: Si piden recomendaciones, sugiere 3 categorías amplias (ej. Fotografías históricas, Documentos fundacionales) con viñetas.
3. Si la respuesta está en la información provista, respóndela de forma directa. No pegues las URLs como texto crudo; si vas a mencionar un documento, cítalo usando Markdown: `[Título del Documento](URL)`.
4. Si la respuesta NO está en la información, di amablemente que no tienes esa información en el catálogo actual. NUNCA inventes enlaces o datos.

FORMATO DE SUGERENCIAS (¡CRÍTICO E INDISPENSABLE!):
Sin importar la pregunta, SIEMPRE debes proporcionar exactamente 3 sugerencias cortas (máximo 6 palabras) al final de tu respuesta para que el usuario pueda seguir explorando.
Debes formatear estas sugerencias AL FINAL de todo tu texto, estrictamente bajo esta palabra clave en mayúsculas (debe estar exactamente así):
SUGERENCIAS:
- Sugerencia 1
- Sugerencia 2
- Sugerencia 3
"""
)
