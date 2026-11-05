import type { ExtractedField } from '../api/types';
import { useDeleteField } from '../hooks/useDeleteField';
import { useUpdateField } from '../hooks/useUpdateField';
import { errorMessage } from '../lib/errorMessages';
import { fieldDisplayStatus } from '../lib/fieldState';
import { formatFieldValue, INVALID_VALUE_REASONS } from '../lib/fieldValue';
import { formatPage } from '../lib/format';
import { CONFIDENCE_LABELS, fieldLabel } from '../lib/labels';
import { DataRow } from './DataRow';
import { FieldEditor } from './FieldEditor';

interface FieldRowProps {
  documentId: string;
  field: ExtractedField;
}

/** `pág. 1 · Confianza alta`: only the parts the API sends. */
function sourceText(field: ExtractedField): string {
  const parts = [];
  if (field.page) parts.push(formatPage(field.page));
  if (field.confidence) parts.push(CONFIDENCE_LABELS[field.confidence]);
  return parts.join(' · ');
}

/**
 * `attempts` counts every LLM call: the first one is not a retry. The reason
 * comes from the value type: the API `error` is technical and in English.
 */
function failureText(field: ExtractedField): string {
  const retries = Math.max(field.attempts - 1, 0);
  const times = `${retries} ${retries === 1 ? 'reintento' : 'reintentos'}`;
  return `Validación fallida tras ${times}: ${INVALID_VALUE_REASONS[field.value_type]}`;
}

/** Note under the value for the statuses that need one. */
function noteText(field: ExtractedField): string | null {
  switch (fieldDisplayStatus(field)) {
    case 'needs_review':
      return 'Confianza baja: revisa antes de usar';
    case 'failed':
      return failureText(field);
    default:
      return null;
  }
}

/** A fixed field of the document type. `document_type` is read-only (`editable: false`). */
export function FieldRow({ documentId, field }: FieldRowProps) {
  const update = useUpdateField(documentId);
  const remove = useDeleteField(documentId);
  const status = fieldDisplayStatus(field);
  const type = field.value_type;
  const label = fieldLabel(field.name);
  const format = (value: ExtractedField['value']) =>
    value === null ? null : formatFieldValue(value, type, field.name);

  return (
    <DataRow
      label={label}
      value={format(field.value)}
      note={noteText(field)}
      original={status === 'edited' ? format(field.original_value) : null}
      meta={sourceText(field)}
      status={status}
      renderEditor={
        field.editable
          ? (close) => (
              <FieldEditor
                fieldLabel={label}
                type={type}
                value={field.value}
                isSaving={update.isPending}
                error={update.isError ? errorMessage(update.error) : null}
                onSave={(value) => update.mutate({ name: field.name, value }, { onSuccess: close })}
                onCancel={() => {
                  update.reset();
                  close();
                }}
              />
            )
          : undefined
      }
      deletion={
        field.editable ? { run: () => remove.mutate(field.name), state: remove } : undefined
      }
    />
  );
}
