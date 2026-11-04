import { ApiError } from '../api/ApiError';

/** Spanish text for each API error code. Unknown codes fall back to the API message. */
const MESSAGES: Record<string, string> = {
  // Upload (synchronous validation in the API)
  invalid_file_type: 'El fichero no es un PDF válido.',
  file_too_large: 'El PDF supera el tamaño máximo permitido.',
  empty_file: 'El fichero está vacío.',
  queue_unavailable: 'No se pudo encolar el procesamiento. Inténtalo de nuevo en unos segundos.',
  // Processing (document `error.code`)
  corrupt_pdf: 'PDF corrupto o cifrado: no se puede leer.',
  no_extractable_text: 'PDF escaneado sin texto extraíble.',
  too_many_pages: 'El PDF tiene demasiadas páginas.',
  extractor_unavailable: 'El extractor de texto no está disponible.',
  processing_failed: 'No se pudo procesar el documento.',
  processing_error: 'Error inesperado al procesar el documento.',
  // LLM
  provider_error: 'Fallo del modelo de lenguaje. Inténtalo de nuevo.',
  provider_timeout: 'El modelo de lenguaje tardó demasiado en responder.',
  // Chat
  rate_limited: 'Has hecho demasiadas preguntas seguidas. Espera un minuto y vuelve a intentarlo.',
  document_not_ready: 'El documento todavía no ha terminado de procesarse.',
  // Field editing
  field_not_found: 'Este campo no existe para el tipo de documento.',
  invalid_field_value: 'El valor no es válido.',
  // Generic
  document_not_found: 'El documento no existe.',
  conversation_not_found: 'La conversación ya no existe. Empieza una nueva.',
  validation_error: 'Datos no válidos.',
  network_error: 'No se pudo conectar con la API.',
};

const FALLBACK = 'Ha ocurrido un error inesperado.';

/** Spanish message for an error code, or `fallback` (the API text) when unknown. */
export function messageForCode(code: string, fallback?: string): string {
  return MESSAGES[code] ?? (fallback || FALLBACK);
}

/** Codes whose API message explains what to fix, so it is shown after the Spanish text. */
const WITH_DETAIL = new Set(['validation_error', 'invalid_field_value']);

/** Spanish message for any thrown value. Validation errors keep the API detail. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const text = messageForCode(error.code, error.message);
    return WITH_DETAIL.has(error.code) && error.message ? `${text} ${error.message}` : text;
  }
  return FALLBACK;
}
