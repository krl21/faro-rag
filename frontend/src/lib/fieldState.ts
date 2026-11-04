import type { ExtractedField } from '../api/types';

/**
 * How a field is shown. `needs_review` is not a backend status: it is a valid
 * value with low confidence. Policy (DECISIONS.md §3): it is never rejected,
 * it is shown with a warning so the user validates it.
 */
export type FieldDisplayStatus = 'ok' | 'needs_review' | 'not_found' | 'failed' | 'edited';

export function fieldDisplayStatus(field: ExtractedField): FieldDisplayStatus {
  if (field.status === 'ok' && field.confidence === 'low') return 'needs_review';
  return field.status;
}
