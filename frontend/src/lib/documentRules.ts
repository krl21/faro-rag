import type { DocumentSummary } from '../api/types';

type RuleInput = Pick<DocumentSummary, 'status' | 'document_type'>;

/** Processed successfully: it has a result to show (fields, or the out-of-scope note). */
export function isProcessed(document: Pick<DocumentSummary, 'status'>): boolean {
  return document.status === 'done';
}

/**
 * Whether a document can be asked about: processed and classified as a policy
 * or an invoice. Documents of type `unknown` are kept and listed, but the
 * backend stores no fragments or fields for them.
 */
export function isQueryable(document: RuleInput): boolean {
  return (
    isProcessed(document) &&
    (document.document_type === 'policy' || document.document_type === 'invoice')
  );
}

/** Processed but outside the scope of the portal (`unknown`). */
export function isOutOfScope(document: RuleInput): boolean {
  return isProcessed(document) && document.document_type === 'unknown';
}
