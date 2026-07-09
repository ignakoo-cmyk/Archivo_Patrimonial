"""
Adaptador de Entrada — Controlador HTTP del Chat (FastAPI)
===========================================================
Traduce las peticiones HTTP al dominio del Chat Context.

REGLAS DE ORO de este controlador:
  1. No contiene lógica de negocio: solo serializa/deserializa y delega.
  2. Gestiona las sesiones a través del SesionRepositorioPort (no directamente
     con un dict), permitiendo cambiar el almacén (Redis, DB) sin modificar aquí.
  3. Los errores del dominio se traducen a códigos HTTP apropiados con JSON descriptivo.
"""

from __future__ import annotations

import traceback
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from Dominio.puertos.puertos_salida import SesionRepositorioPort
from Aplicacion.dtos.chat_dtos import (
    DocumentoReferenciaDTO,
    MensajeEntradaDTO,
    MensajeRespuestaDTO,
)

logger = logging.getLogger("chat_service.controlador")

# ── Router ───────────────────────────────────────────────────────────────────

router = APIRouter(prefix="/api/v1/chat", tags=["Chat Conversacional"])


@router.post(
    "/message",
    summary="Enviar mensaje al asistente del Archivo Patrimonial",
)
async def enviar_mensaje(
    cuerpo: MensajeEntradaDTO,
    request: Request,
) -> JSONResponse:
    """
    Procesa un mensaje del usuario mediante el orquestador del dominio.
    Ejecuta el flujo completo: evaluación de intención → RAG → LLM → validación.
    En caso de error, retorna un JSON diagnóstico con tipo, causa y stack trace.
    """
    orquestador = request.app.state.orquestador
    sesion_repo: SesionRepositorioPort = request.app.state.sesion_repositorio

    # ── Recuperar o crear la sesión ──────────────────────────────────────────
    try:
        sesion = sesion_repo.obtener_o_crear(cuerpo.conversation_id)
    except Exception as err:
        tb = traceback.format_exc()
        logger.error("❌ [SESIÓN] No se pudo recuperar la sesión.\n%s", tb)
        return JSONResponse(status_code=503, content={
            "success": False,
            "error_type": "SESSION_STORE_ERROR",
            "message": "Error al acceder al repositorio de sesiones (Redis/DB).",
            "cause": str(err),
            "stack_trace": tb,
        })

    # ── Llamar al orquestador (RAG + LLM) ───────────────────────────────────
    try:
        respuesta, docs_recuperados, sugerencias = await orquestador.procesar_mensaje(
            sesion, cuerpo.message
        )
        sesion_repo.guardar(sesion)

    except RuntimeError as err:
        tb = traceback.format_exc()
        mensaje_err = str(err)

        # Detectar errores de Gemini API (503 sobrecarga, 429 rate-limit, 404 modelo)
        if "503" in mensaje_err or "UNAVAILABLE" in mensaje_err:
            logger.error("❌ [GEMINI 503] Servicio no disponible por alta demanda.\n%s", tb)
            return JSONResponse(status_code=503, content={
                "success": False,
                "error_type": "LLM_UNAVAILABLE",
                "message": "El modelo de lenguaje está saturado. Intenta en unos segundos.",
                "cause": mensaje_err,
                "stack_trace": tb,
            })

        if "429" in mensaje_err or "RESOURCE_EXHAUSTED" in mensaje_err:
            logger.error("❌ [GEMINI 429] Cuota de API agotada.\n%s", tb)
            return JSONResponse(status_code=429, content={
                "success": False,
                "error_type": "LLM_RATE_LIMIT",
                "message": "Cuota de la API de Gemini agotada temporalmente.",
                "cause": mensaje_err,
                "stack_trace": tb,
            })

        if "404" in mensaje_err or "NOT_FOUND" in mensaje_err:
            logger.error("❌ [GEMINI 404] Modelo no encontrado.\n%s", tb)
            return JSONResponse(status_code=500, content={
                "success": False,
                "error_type": "LLM_MODEL_NOT_FOUND",
                "message": "El modelo de Gemini configurado no existe o no está disponible.",
                "cause": mensaje_err,
                "stack_trace": tb,
            })

        # Error de runtime genérico
        logger.error("❌ [RUNTIME] Error en orquestador.\n%s", tb)
        return JSONResponse(status_code=500, content={
            "success": False,
            "error_type": "ORCHESTRATOR_RUNTIME_ERROR",
            "message": "Error interno en el servicio de chat.",
            "cause": mensaje_err,
            "stack_trace": tb,
        })

    except ConnectionError as err:
        tb = traceback.format_exc()
        logger.error("❌ [CONEXIÓN] Fallo al conectar con servicio externo (ChromaDB/Redis).\n%s", tb)
        return JSONResponse(status_code=502, content={
            "success": False,
            "error_type": "EXTERNAL_SERVICE_UNREACHABLE",
            "message": "No se pudo conectar con ChromaDB o el servicio de búsqueda.",
            "cause": str(err),
            "stack_trace": tb,
        })

    except TimeoutError as err:
        tb = traceback.format_exc()
        logger.error("❌ [TIMEOUT] El servicio externo no respondió a tiempo.\n%s", tb)
        return JSONResponse(status_code=504, content={
            "success": False,
            "error_type": "EXTERNAL_SERVICE_TIMEOUT",
            "message": "Timeout: el servicio de búsqueda o la API de Gemini tardaron demasiado.",
            "cause": str(err),
            "stack_trace": tb,
        })

    except Exception as err:
        tb = traceback.format_exc()
        logger.error("❌ [INESPERADO] Error no controlado en el endpoint de chat.\n%s", tb)
        return JSONResponse(status_code=500, content={
            "success": False,
            "error_type": "UNEXPECTED_ERROR",
            "message": "Error inesperado. Revisa los logs del servidor para más detalles.",
            "cause": str(err),
            "stack_trace": tb,
        })

    # ── Ensamblar respuesta de éxito ─────────────────────────────────────────
    documentos_referencia = [
        DocumentoReferenciaDTO(
            title=doc.titulo,
            href=doc.url_catalogo,
            relevance_score=doc.puntuacion_relevancia,
            description=doc.descripcion
        )
        for doc in docs_recuperados
    ]

    return JSONResponse(status_code=200, content=MensajeRespuestaDTO(
        success=True,
        response=respuesta,
        conversation_id=cuerpo.conversation_id,
        documents=documentos_referencia,
        rich_cards=[],
        quick_replies=sugerencias
    ).model_dump())

