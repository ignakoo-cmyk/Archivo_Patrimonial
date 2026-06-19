"""
Adaptador de Entrada — Controlador HTTP del Chat (FastAPI)
===========================================================
Traduce las peticiones HTTP al dominio del Chat Context.
No contiene lógica de negocio: solo serializa/deserializa y delega al caso de uso.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from Dominio.entidades.sesion_chat import SesionChat
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
    sesiones: dict[str, SesionChat] = request.app.state.sesiones

    # Recuperar o crear la sesión de chat
    if cuerpo.conversation_id not in sesiones:
        sesiones[cuerpo.conversation_id] = SesionChat(id=cuerpo.conversation_id)
    sesion = sesiones[cuerpo.conversation_id]

    try:
        respuesta, docs_recuperados = await orquestador.procesar_mensaje(sesion, cuerpo.message)
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar el mensaje: {error}"
        ) from error

    # Mapear los documentos recuperados al DTO de salida
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
        quick_replies=[]
    )
