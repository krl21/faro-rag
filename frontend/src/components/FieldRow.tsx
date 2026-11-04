import { useState } from 'react';
import type { ExtractedField, FieldValue } from '../api/types';
import { useUpdateField } from '../hooks/useUpdateField';
import { errorMessage } from '../lib/errorMessages';
import { fieldDisplayStatus } from '../lib/fieldState';
import { formatFieldValue, INVALID_VALUE_REASONS } from '../lib/fieldValue';
import { formatPage } from '../lib/format';
import { CONFIDENCE_LABELS, fieldLabel } from '../lib/labels';
import { STATUS_APPEARANCE } from '../lib/statusAppearance';
import { Button } from './Button';
import { FieldEditor } from './FieldEditor';
import styles from './FieldRow.module.css';
import { EditIcon } from './icons/icons';
import { StatusBadge } from './StatusBadge';

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

export function FieldRow({ documentId, field }: FieldRowProps) {
  const [isEditing, setIsEditing] = useState(false);
  const update = useUpdateField(documentId);
  const status = fieldDisplayStatus(field);
  const type = field.value_type;
  const label = fieldLabel(field.name);
  const note = noteText(field);
  const source = sourceText(field);

  const save = (value: FieldValue) =>
    update.mutate({ name: field.name, value }, { onSuccess: () => setIsEditing(false) });

  const cancel = () => {
    update.reset();
    setIsEditing(false);
  };

  return (
    <li className={styles.row} data-tone={STATUS_APPEARANCE[status].tone}>
      <span className={styles.name}>{label}</span>
      <div className={styles.value}>
        {field.value === null ? (
          <span className={styles.missing}>Sin valor</span>
        ) : (
          formatFieldValue(field.value, type, field.name)
        )}
        {note && <p className={styles.note}>{note}</p>}
        {status === 'edited' && field.original_value != null && (
          <p className={styles.original}>
            Valor extraído: {formatFieldValue(field.original_value, type, field.name)}
          </p>
        )}
      </div>
      <span className={styles.meta}>{source}</span>
      <div className={styles.side}>
        <StatusBadge status={status} />
        {field.editable && !isEditing && (
          <Button
            variant="ghost"
            icon={<EditIcon size={18} />}
            aria-label={`Editar ${label}`}
            title="Editar valor"
            onClick={() => setIsEditing(true)}
          />
        )}
      </div>
      {isEditing && (
        <div className={styles.editor}>
          <FieldEditor
            fieldLabel={label}
            type={type}
            value={field.value}
            isSaving={update.isPending}
            error={update.isError ? errorMessage(update.error) : null}
            onSave={save}
            onCancel={cancel}
          />
        </div>
      )}
    </li>
  );
}
