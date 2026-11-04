import type { DocumentStatus } from './DocumentStatus';

/** Result of `POST /documents`. */
export interface DocumentUploadResponse {
  id: string;
  status: DocumentStatus;
  /** `true` when a file with the same content already existed. */
  duplicate: boolean;
  message: string | null;
}
