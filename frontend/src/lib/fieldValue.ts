import type { FieldValue, FieldValueType, Money, Period } from '../api/types';
import { formatDate, formatMoney } from './format';
import { valueLabel } from './labels';

/**
 * Human-readable value. With `fieldName`, coded values are translated
 * (`document_type: policy` -> `Póliza`).
 */
export function formatFieldValue(value: FieldValue, type: FieldValueType, fieldName = ''): string {
  switch (type) {
    case 'date':
      return formatDate(String(value));
    case 'period': {
      const { start, end } = value as Period;
      return `${formatDate(start)} – ${formatDate(end)}`;
    }
    case 'money': {
      const { amount, currency } = value as Money;
      return formatMoney(amount, currency);
    }
    case 'text_list':
      return (value as string[]).map((item) => valueLabel(fieldName, item)).join(', ');
    default:
      return valueLabel(fieldName, String(value));
  }
}

// --- Editing ----------------------------------------------------------------

/** One input of the editor of a value type. */
export interface EditorInput {
  key: string;
  label: string;
  kind: 'text' | 'textarea' | 'date' | 'number';
  hint?: string;
}

/** Inputs of each value type: the editor is generic and renders these. */
export const EDITOR_INPUTS: Record<FieldValueType, EditorInput[]> = {
  text: [{ key: 'value', label: 'Valor', kind: 'text' }],
  long_text: [{ key: 'value', label: 'Valor', kind: 'textarea' }],
  date: [{ key: 'value', label: 'Fecha', kind: 'date' }],
  period: [
    { key: 'start', label: 'Desde', kind: 'date' },
    { key: 'end', label: 'Hasta', kind: 'date' },
  ],
  money: [
    { key: 'amount', label: 'Importe', kind: 'number' },
    { key: 'currency', label: 'Moneda', kind: 'text', hint: 'Código ISO, p. ej. EUR' },
  ],
  text_list: [{ key: 'value', label: 'Valores', kind: 'textarea', hint: 'Uno por línea' }],
};

/** Form state of the editor: one string per input. */
export type Draft = Record<string, string>;

/** Value -> form state. A missing value gives empty inputs. */
export function toDraft(value: FieldValue | null, type: FieldValueType): Draft {
  if (value === null) {
    return Object.fromEntries(EDITOR_INPUTS[type].map((input) => [input.key, '']));
  }
  switch (type) {
    case 'period': {
      const { start, end } = value as Period;
      return { start, end };
    }
    case 'money': {
      const { amount, currency } = value as Money;
      return { amount: String(amount), currency };
    }
    case 'text_list':
      return { value: (value as string[]).join('\n') };
    default:
      return { value: String(value) };
  }
}

/**
 * Form state -> value sent to the API. Only trims and reshapes: the API
 * validates the value with the same rules as the extraction.
 *
 * @returns The value, or `null` when a required input is empty.
 */
export function fromDraft(draft: Draft, type: FieldValueType): FieldValue | null {
  const get = (key: string) => (draft[key] ?? '').trim();
  const isComplete = EDITOR_INPUTS[type].every((input) => get(input.key) !== '');
  if (!isComplete) return null;

  switch (type) {
    case 'period':
      return { start: get('start'), end: get('end') };
    case 'money':
      return { amount: get('amount'), currency: get('currency').toUpperCase() };
    case 'text_list': {
      const items = get('value')
        .split('\n')
        .map((item) => item.trim())
        .filter(Boolean);
      return items;
    }
    default:
      return get('value');
  }
}
