import { ApiError } from '../api/ApiError';
import type { DocumentError } from '../api/types';

/**
 * What the user reads for each API error code: the problem and, when there is
 * one, what to do. Never codes, HTTP statuses or the API text (technical, in English).
 */
const MESSAGES: Record<string, string> = {
  // Upload (synchronous validation in the API)
  invalid_file_type: 'El fichero no es un PDF válido.',
  file_too_large: 'El PDF supera el tamaño máximo permitido.',
  empty_file: 'El fichero está vacío.',
  queue_unavailable: 'No se pudo poner el documento en cola. Inténtalo de nuevo en unos segundos.',
  // Processing (document `error.code`)
  corrupt_pdf: 'PDF corrupto o cifrado: no se puede leer.',
  no_extractable_text: 'PDF escaneado sin texto extraíble.',
  too_many_pages: 'El PDF tiene demasiadas páginas.',
  extractor_unavailable: 'El extractor de texto no está disponible.',
  processing_failed: 'No se pudo procesar el documento.',
  processing_error: 'Error inesperado al procesar el documento.',
  // LLM
  provider_error: 'Fallo del modelo de lenguaje. Inténtalo de nuevo.',
  provider_timeout: 'El modelo de lenguaje tardó demasiado en responder. Inténtalo de nuevo.',
  // Chat
  rate_limited: 'Has hecho demasiadas preguntas seguidas. Espera un minuto y vuelve a intentarlo.',
  document_not_ready: 'El documento todavía no ha terminado de procesarse.',
  document_not_queryable:
    'No es una póliza ni una factura: no tiene campos extraídos y no se puede consultar.',
  // Field editing
  field_not_found: 'Este campo no existe para el tipo de documento.',
  invalid_field_value: 'El valor no es válido. Revisa el formato e inténtalo de nuevo.',
  // Generic
  document_not_found: 'El documento ya no existe.',
  conversation_not_found: 'La conversación ya no existe. Empieza una nueva.',
  validation_error: 'Los datos enviados no son válidos. Revísalos e inténtalo de nuevo.',
  network_error: 'No se pudo conectar con el servidor. Comprueba tu conexión.',
};

const UNEXPECTED = 'Ha ocurrido un error inesperado. Inténtalo de nuevo.';
const SERVER_UNAVAILABLE =
  'El servidor no está disponible en este momento. Inténtalo de nuevo en unos segundos.';

/** Message from the HTTP status, for answers without a known code (for example a proxy 502). */
function messageForStatus(status: number): string {
  if (status === 413) return MESSAGES.file_too_large as string;
  if (status === 429) return MESSAGES.rate_limited as string;
  if (status === 502 || status === 503 || status === 504) return SERVER_UNAVAILABLE;
  if (status >= 400 && status < 500) return MESSAGES.validation_error as string;
  return UNEXPECTED;
}

/** Spanish message for an error code; `fallback` (also Spanish) for unknown codes. */
export function messageForCode(code: string, fallback = UNEXPECTED): string {
  return MESSAGES[code] ?? fallback;
}

/** Why a document failed to process, for the table and the fields view. */
export function documentErrorMessage(error: DocumentError): string {
  return messageForCode(error.code, MESSAGES.processing_failed);
}

/** Note for documents of type `other`: processed, but not queryable. */
export const OUT_OF_SCOPE_MESSAGE = MESSAGES.document_not_queryable as string;

/** Spanish message for any thrown value: by code, then by HTTP status. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return MESSAGES[error.code] ?? messageForStatus(error.status);
  }
  return UNEXPECTED;
}
