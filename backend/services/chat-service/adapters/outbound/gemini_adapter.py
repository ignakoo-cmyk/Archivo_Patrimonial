"""
Adaptador de Salida — Google Gemini
=====================================
Implementa ModeloLenguajePort usando la librería google.generativeai.
Todo el código de infraestructura de Gemini se concentra aquí.

Si en el futuro se migra a OpenAI GPT u otro LLM, SOLO este archivo cambia.
"""

from __future__ import annotations

import google.generativeai as genai

from domain.chat_context.models import PromptContextualizado
from domain.chat_context.ports import ModeloLenguajePort


class GeminiAdapter(ModeloLenguajePort):
    """
    Adaptador de Salida concreto para Google Gemini.
    Implementa el contrato ModeloLenguajePort.
    """

    MODELO_PRODUCCION = "gemini-2.5-flash"

    def __init__(self, api_key: str, nombre_modelo: str = MODELO_PRODUCCION) -> None:
        """
        Args:
            api_key:       Clave de API de Google AI Studio.
            nombre_modelo: Identificador del modelo Gemini a usar.
        """
        self._disponible = False
        if not api_key:
            print("⚠️ [GeminiAdapter] Sin GEMINI_API_KEY. Operando en modo fallback.")
            self._modelo = None
            return

        try:
            genai.configure(api_key=api_key)
            self._modelo = genai.GenerativeModel(nombre_modelo)
            self._disponible = True
            print(f"✅ [GeminiAdapter] Modelo '{nombre_modelo}' configurado correctamente.")
        except Exception as error:
            print(f"❌ [GeminiAdapter] Error al configurar Gemini: {error}")
            self._modelo = None

    def esta_disponible(self) -> bool:
        return self._disponible and self._modelo is not None

    async def generar_respuesta(self, prompt: PromptContextualizado) -> str:
        """Envía el prompt a Gemini y retorna el texto generado."""
        if not self.esta_disponible():
            raise RuntimeError("[GeminiAdapter] El modelo no está disponible.")
        try:
            response = await self._modelo.generate_content_async(prompt.texto_completo)
            return response.text
        except Exception as error:
            raise RuntimeError(f"[GeminiAdapter] Error de generación: {error}") from error
