import type { Confidence } from './Confidence';
import type { FieldStatus } from './FieldStatus';
import type { FieldValue } from './FieldValue';
import type { FieldValueType } from './FieldValueType';

/**
 * A structured field extracted from a document.
 * `confidence` is `null` for missing, failed and edited values.
 */
export interface ExtractedField {
  name: string;
  value: FieldValue | null;
  confidence: Confidence | null;
  status: FieldStatus;
  error: string | null;
  attempts: number;
  /** 1-based page the value comes from, when known. */
  page: number | null;
  value_type: FieldValueType;
  /** `false` only for `document_type`. */
  editable: boolean;
  /** Value extracted by the LLM before the first user edit. */
  original_value: FieldValue | null;
  edited_at: string | null;
}
