import type { FactValue } from './FactValue';

/**
 * A free datum of a document: a `label: value` line or a table row. Unlike the
 * fixed fields, it is not part of the document type; the user can edit and delete it.
 */
export interface DocumentFact {
  id: number;
  /** For a table row, the text of its first non-empty cell. */
  label: string;
  value: FactValue;
  /** 1-based page, when known. */
  page: number | null;
  table_index: number | null;
  row_index: number | null;
  status: 'ok' | 'edited';
  /** Label and value as extracted, before the first user edit. */
  original_value: { label: string; value: FactValue } | null;
  edited_at: string | null;
}
