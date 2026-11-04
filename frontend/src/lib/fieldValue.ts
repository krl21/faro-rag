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

/**
 * Why an extracted value of this type can be rejected. Shown instead of the
 * API `error`, which is a technical text in English.
 */
export const INVALID_VALUE_REASONS: Record<FieldValueType, string> = {
  text: 'el texto extraído no es válido',
  long_text: 'el texto extraído no es válido',
  date: 'la fecha extraída no es válida',
  period: 'las fechas de vigencia no son válidas',
  money: 'el importe o la moneda no son válidos',
  text_list: 'la lista extraída no es válida',
};

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

const CURRENCY = /^[A-Za-z]{3}$/;

/**
 * Problems the user can fix before saving, in Spanish. The API validates
 * again; these checks only explain the usual mistakes.
 *
 * @returns The problem, or `null` when the draft looks valid.
 */
export function draftError(draft: Draft, type: FieldValueType): string | null {
  const get = (key: string) => (draft[key] ?? '').trim();
  if (type === 'period' && get('start') && get('end') && get('end') < get('start')) {
    return 'La fecha de fin no puede ser anterior a la de inicio.';
  }
  if (type === 'money') {
    const amount = get('amount');
    if (amount && !(Number(amount) >= 0))
      return 'El importe debe ser un número igual o mayor que 0.';
    const currency = get('currency');
    if (currency && !CURRENCY.test(currency)) {
      return 'La moneda debe ser un código de 3 letras, por ejemplo EUR.';
    }
  }
  return null;
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
