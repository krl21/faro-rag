import { config } from '../config';
import { ApiError, NETWORK_ERROR, UNKNOWN_ERROR } from './ApiError';

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE';
  /** JSON body; `FormData` is sent as multipart. */
  body?: unknown;
  /** Non-2xx statuses whose body is still a valid result (for example 503 in readiness). */
  acceptStatuses?: number[];
}

/**
 * Turn an error body into an `ApiError`. The API answers
 * `{"error": {"code", "message"}}`; FastAPI validation errors answer `{"detail": [...]}`.
 */
function toApiError(status: number, body: unknown): ApiError {
  const error = (body as { error?: { code?: string; message?: string } } | null)?.error;
  if (error?.code) return new ApiError(status, error.code, error.message ?? '');

  const detail = (body as { detail?: unknown } | null)?.detail;
  if (Array.isArray(detail)) {
    const messages = detail.map((d: { msg?: string }) => d.msg).filter(Boolean);
    return new ApiError(status, 'validation_error', messages.join('; '));
  }
  if (typeof detail === 'string') return new ApiError(status, UNKNOWN_ERROR, detail);
  return new ApiError(status, UNKNOWN_ERROR, `HTTP ${status}`);
}

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

/**
 * Call the API and return the parsed JSON body (`null` for an empty one, such as a 204).
 *
 * @throws ApiError on a network failure or a non-accepted status.
 */
export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, acceptStatuses = [] } = options;
  const isForm = body instanceof FormData;
  const init: RequestInit = {
    method,
    headers: body === undefined || isForm ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : isForm ? body : JSON.stringify(body),
  };

  let response: Response;
  try {
    // Resolved against the page origin: `/api` (proxy) or an absolute base URL both work.
    const url = new URL(`${config.apiBaseUrl}${path}`, window.location.origin);
    response = await fetch(url, init);
  } catch (cause) {
    throw new ApiError(0, NETWORK_ERROR, cause instanceof Error ? cause.message : String(cause));
  }

  const data = await readJson(response);
  if (response.ok || acceptStatuses.includes(response.status)) return data as T;
  throw toApiError(response.status, data);
}
