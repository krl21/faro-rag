import type { FactUpdate, FactValue } from '../api/types';

/** Limits of the API (`invalid_fact_value` beyond them). */
export const FACT_LABEL_MAX = 60;
export const FACT_VALUE_MAX = 300;
export const FACT_MAX_COLUMNS = 30;

/** `Cantidad: 1 ud; Importe: 1.280,00 €` for a table row; the text as is otherwise. */
export function formatFactValue(value: FactValue): string {
  if (typeof value === 'string') return value;
  return Object.entries(value)
    .map(([column, cell]) => `${column}: ${cell}`)
    .join('; ');
}

// --- Editing ----------------------------------------------------------------

/** One column of a table row in the editor. */
export interface ColumnDraft {
  name: string;
  value: string;
}

/** Form state of the editor: a text value, or the columns of a table row. */
export type FactDraft =
  | { kind: 'text'; label: string; text: string }
  | { kind: 'row'; label: string; columns: ColumnDraft[] };

export function toFactDraft(label: string, value: FactValue): FactDraft {
  if (typeof value === 'string') return { kind: 'text', label, text: value };
  const columns = Object.entries(value).map(([name, cell]) => ({ name, value: cell }));
  return { kind: 'row', label, columns };
}

/** Columns that will be sent: the API drops empty cells, so the editor does too. */
function filledColumns(columns: ColumnDraft[]): ColumnDraft[] {
  return columns
    .map((column) => ({ name: column.name.trim(), value: column.value.trim() }))
    .filter((column) => column.value !== '');
}

function rowError(columns: ColumnDraft[]): string | null {
  const filled = filledColumns(columns);
  if (filled.length === 0) return 'La fila necesita al menos una columna con valor.';
  if (filled.length > FACT_MAX_COLUMNS) {
    return `Una fila admite como máximo ${FACT_MAX_COLUMNS} columnas.`;
  }
  if (filled.some((column) => column.name === '')) {
    return 'Cada columna con valor necesita un nombre.';
  }
  const names = filled.map((column) => column.name);
  if (new Set(names).size !== names.length) return 'Hay dos columnas con el mismo nombre.';
  if (filled.some((column) => column.value.length > FACT_VALUE_MAX)) {
    return `Cada valor admite como máximo ${FACT_VALUE_MAX} caracteres.`;
  }
  return null;
}

/**
 * Problems the user can fix before saving, in Spanish. The API validates again.
 *
 * @returns The problem, or `null` when the draft looks valid.
 */
export function factDraftError(draft: FactDraft): string | null {
  const label = draft.label.trim();
  if (label === '') return 'La etiqueta no puede estar vacía.';
  if (label.length > FACT_LABEL_MAX) {
    return `La etiqueta admite como máximo ${FACT_LABEL_MAX} caracteres.`;
  }
  if (draft.kind === 'row') return rowError(draft.columns);
  const text = draft.text.trim();
  if (text === '') return 'El valor no puede estar vacío.';
  if (text.length > FACT_VALUE_MAX) {
    return `El valor admite como máximo ${FACT_VALUE_MAX} caracteres.`;
  }
  return null;
}

/**
 * Form state -> body of the PATCH. Label and value are always sent: the API
 * does not derive the label from the first column of a row.
 *
 * @returns The body, or `null` when the draft is not valid.
 */
export function fromFactDraft(draft: FactDraft): Required<FactUpdate> | null {
  if (factDraftError(draft)) return null;
  const label = draft.label.trim();
  if (draft.kind === 'text') return { label, value: draft.text.trim() };
  const value = Object.fromEntries(
    filledColumns(draft.columns).map((column) => [column.name, column.value]),
  );
  return { label, value };
}
