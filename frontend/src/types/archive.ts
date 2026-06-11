/**
 * Contratos de Datos para el Frontend -- Archivo Patrimonial UAH
 * ==================================================================
 * Interfaces TypeScript que tipan las respuestas del backend.
 * Estas definiciones constituyen el contrato entre la capa de presentacion
 * (Next.js) y la capa de aplicacion (Python/FastAPI).
 *
 * Deben mantenerse sincronizadas con los DTOs que devuelven los endpoints
 * /api/v1/archive/search y /api/v1/archive/documents/{codigo}.
 *
 * Nota para el equipo de frontend:
 *   El backend puede arrancar en modo Mock (USE_MOCK_ADAPTER=true) para
 *   que se pueda maquetar la UI con datos realistas sin dependencia del
 *   sistema AtoM. Los tipos aqui definidos son identicos en ambos modos.
 */

// -- Entidades de dominio serializadas --

export interface ObjetoDigital {
  url: string;
  tipo_mime: string;
  etiqueta: string;
}

export interface DocumentoPatrimonial {
  id: string;
  codigo_referencia: string;
  titulo: string;
  anio: string | null;
  url_sistema: string;
  alcance_y_contenido: string;
  creadores: string[];
  materias: string[];
  cobertura: string[];
  objetos_digitales: ObjetoDigital[];
  relevancia: number;
}

// -- Componentes de UI --

/**
 * QuickReply: Boton de sugerencia contextual que aparece debajo del mensaje
 * del chatbot. Al hacer clic, envia el valor como nueva consulta.
 */
export interface QuickReply {
  label: string;
  value: string;
}

/**
 * RichCard: Tarjeta enriquecida para renderizar un documento patrimonial
 * directamente en la conversacion del chatbot. Incluye miniatura, titulo,
 * codigo de referencia y un enlace al catalogo.
 */
export interface RichCard {
  id: string;
  titulo: string;
  codigo_referencia: string;
  anio: string | null;
  url: string;
  descripcion_corta: string;
  materias: string[];
  miniatura_url: string | null;
  relevancia: number;
}

// -- Respuestas del API --

/**
 * RespuestaBusquedaResponse: Respuesta del endpoint de busqueda.
 * Contiene el mensaje textual, las Rich Cards para renderizar los
 * resultados y los Quick Replies para guiar la conversacion.
 */
export interface RespuestaBusquedaResponse {
  success: boolean;
  mensaje: string;
  documentos: DocumentoPatrimonial[];
  rich_cards: RichCard[];
  quick_replies: QuickReply[];
  total: number;
}

/**
 * RespuestaDetalleResponse: Respuesta del endpoint de detalle de documento.
 */
export interface RespuestaDetalleResponse {
  success: boolean;
  mensaje: string;
  documento: DocumentoPatrimonial | null;
  rich_card?: RichCard;
  quick_replies: QuickReply[];
}

/**
 * RespuestaChatbotResponse: Tipo unificado que el componente de chat
 * utiliza internamente para manejar cualquier respuesta del backend.
 * Combina el mensaje de la IA (generado por el Chat Service) con los
 * datos estructurados del Archive Service.
 */
export interface RespuestaChatbotResponse {
  /** Mensaje de texto principal generado por el bot (Markdown) */
  mensaje: string;

  /** Documentos encontrados como resultado de la busqueda */
  documentos?: DocumentoPatrimonial[];

  /** Tarjetas enriquecidas para la UI, con miniaturas y metadata resumida */
  rich_cards?: RichCard[];

  /** Botones de sugerencia contextual para guiar al usuario */
  quick_replies?: QuickReply[];

  /** Indica si la respuesta fue exitosa */
  success: boolean;
}
