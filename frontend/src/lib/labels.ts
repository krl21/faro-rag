import type { Confidence, DocumentType } from '../api/types';

export const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  policy: 'Póliza',
  invoice: 'Factura',
  unknown: 'Desconocido',
};

export const CONFIDENCE_LABELS: Record<Confidence, string> = {
  low: 'Confianza baja',
  medium: 'Confianza media',
  high: 'Confianza alta',
};

/**
 * Translation of the coded values of a field (the API returns codes in
 * English). Fields not listed here hold free text, shown as is.
 */
const VALUE_LABELS: Record<string, Record<string, string>> = {
  document_type: DOCUMENT_TYPE_LABELS,
};

/** Spanish label of a coded value (`document_type: policy` -> `Póliza`); other values unchanged. */
export function valueLabel(fieldName: string, value: string): string {
  return VALUE_LABELS[fieldName]?.[value] ?? value;
}

/** Spanish names of the fields the backend extracts (`field_specs.py`). */
const FIELD_LABELS: Record<string, string> = {
  document_type: 'Tipo de documento',
  policy_number: 'Número de póliza',
  validity: 'Vigencia',
  coverages: 'Coberturas',
  invoice_amount: 'Monto de la factura',
  invoice_date: 'Fecha de la factura',
  holder: 'Titular',
  tax_id: 'NIF',
  license_plate: 'Matrícula',
};

export function documentTypeLabel(type: DocumentType | null): string {
  return type ? DOCUMENT_TYPE_LABELS[type] : 'Sin clasificar';
}

/** Label of a field; unknown names are shown humanized (`foo_bar` -> `Foo bar`). */
export function fieldLabel(name: string): string {
  const label = FIELD_LABELS[name];
  if (label) return label;
  const text = name.replace(/_/g, ' ');
  return text.charAt(0).toUpperCase() + text.slice(1);
}
