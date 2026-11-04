import type { DocumentError } from './DocumentError';
import type { DocumentStatus } from './DocumentStatus';
import type { DocumentType } from './DocumentType';

/** A document as shown in lists (`GET /documents`). */
export interface DocumentSummary {
  id: string;
  filename: string;
  status: DocumentStatus;
  document_type: DocumentType | null;
  page_count: number | null;
  size_bytes: number;
  error: DocumentError | null;
  created_at: string;
  updated_at: string;
}
