"""
Adaptador de Entrada — Controlador HTTP del Chat (FastAPI)
===========================================================
Traduce las peticiones HTTP al dominio del Chat Context.

REGLAS DE ORO de este controlador:
  1. No contiene lógica de negocio: solo serializa/deserializa y delega.
  2. Gestiona las sesiones a través del SesionRepositorioPort (no directamente
     con un dict), permitiendo cambiar el almacén (Redis, DB) sin modificar aquí.
  3. Los errores del dominio se traducen a códigos HTTP apropiados.
"""

from __future__ import annotations

import traceback

from fastapi import APIRouter, HTTPException, Request

from Dominio.puertos.puertos_salida import SesionRepositorioPort
from Aplicacion.dtos.chat_dtos import (
    DocumentoReferenciaDTO,
    MensajeEntradaDTO,
    MensajeRespuestaDTO,
)


# ── Router ───────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/v1/chat", tags=["Chat Conversacional"])


@router.post(
    "/message",
    response_model=MensajeRespuestaDTO,
    summary="Enviar mensaje al asistente del Archivo Patrimonial",
)
async def enviar_mensaje(
    cuerpo: MensajeEntradaDTO,
    request: Request,
) -> MensajeRespuestaDTO:
    """
    Procesa un mensaje del usuario mediante el orquestador del dominio.
    Ejecuta el flujo completo: evaluación de intención → RAG → LLM → validación.
    """
    orquestador = request.app.state.orquestador
    sesion_repo: SesionRepositorioPort = request.app.state.sesion_repositorio

    # Recuperar o crear la sesión a través del puerto de repositorio
    sesion = sesion_repo.obtener_o_crear(cuerpo.conversation_id)

    try:
        respuesta, docs_recuperados, sugerencias = await orquestador.procesar_mensaje(
            sesion, cuerpo.message
        )
        # Persistir la sesión actualizada
        sesion_repo.guardar(sesion)
    except Exception as error:
        print(f"Error crítico en endpoint chat/message: {str(error)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar el mensaje: {str(error)}"
        ) from error

    documentos_referencia = [
        DocumentoReferenciaDTO(
            title=doc.titulo,
            href=doc.url_catalogo,
            relevance_score=doc.puntuacion_relevancia,
            description=doc.descripcion
        )
        for doc in docs_recuperados
    ]

    return MensajeRespuestaDTO(
        success=True,
        response=respuesta,
        conversation_id=cuerpo.conversation_id,
        documents=documentos_referencia,
        rich_cards=[],
        quick_replies=sugerencias
    )
