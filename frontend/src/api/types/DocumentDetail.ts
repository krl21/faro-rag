import type { DocumentSummary } from './DocumentSummary';
import type { ExtractedField } from './ExtractedField';

/** A document with its extracted fields (`GET /documents/{id}`). */
export interface DocumentDetail extends DocumentSummary {
  chunk_count: number;
  fields: ExtractedField[];
}
