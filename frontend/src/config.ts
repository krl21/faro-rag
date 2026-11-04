/**
 * Runtime settings, read from the environment at build time.
 * No URL or key is hard-coded: the API is reached through the `/api` proxy
 * (Vite in development, nginx in production).
 */
const env = import.meta.env;

export const config = {
  /** Base path of the API. */
  apiBaseUrl: env.VITE_API_BASE_URL ?? '/api',
  /** Client-side upload limit; must match `MAX_UPLOAD_MB` of the API. */
  maxUploadBytes: Number(env.VITE_MAX_UPLOAD_MB ?? 20) * 1024 * 1024,
  /** Polling interval while a document is pending or processing. */
  documentPollMs: 3000,
  /** Polling interval of the health indicator. */
  healthPollMs: 15000,
  /** Question length accepted by the API. */
  questionMinLength: 3,
  questionMaxLength: 1000,
} as const;
