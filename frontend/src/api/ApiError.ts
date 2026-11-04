/** Error returned by the API (or a network failure, with `status` 0). */
export class ApiError extends Error {
  readonly status: number;
  /** Machine-readable code from `{"error": {"code": ...}}`. */
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

/** Code used when the request never reached the API. */
export const NETWORK_ERROR = 'network_error';
/** Code used when the API answered with an unexpected body. */
export const UNKNOWN_ERROR = 'unknown_error';
