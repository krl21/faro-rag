import type { DocumentSummary } from '../api/types';

/**
 * Whether a document can be asked about: processed and classified as a policy
 * or an invoice. Documents of type `other` are kept and listed, but the
 * backend stores no fragments or fields for them.
 */
export function isQueryable(document: Pick<DocumentSummary, 'status' | 'document_type'>): boolean {
  return (
    document.status === 'done' &&
    (document.document_type === 'policy' || document.document_type === 'invoice')
  );
}

/** Processed but outside the scope of the portal (`other`). */
export function isOutOfScope(document: Pick<DocumentSummary, 'status' | 'document_type'>): boolean {
  return document.status === 'done' && document.document_type === 'other';
}
