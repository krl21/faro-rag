import type { DocumentFact } from './DocumentFact';
import type { DocumentSummary } from './DocumentSummary';
import type { ExtractedField } from './ExtractedField';

/** A document with its fixed fields and free data (`GET /documents/{id}`). */
export interface DocumentDetail extends DocumentSummary {
  chunk_count: number;
  fields: ExtractedField[];
  /** Free data (`label: value` lines and table rows), in page and table order. */
  facts: DocumentFact[];
}
