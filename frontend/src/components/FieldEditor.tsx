import { useState, type FormEvent } from 'react';
import type { FieldValue, FieldValueType } from '../api/types';
import { EDITOR_INPUTS, fromDraft, toDraft, type EditorInput } from '../lib/fieldValue';
import { Button } from './Button';
import styles from './FieldEditor.module.css';
import forms from './forms.module.css';

interface FieldEditorProps {
  fieldLabel: string;
  type: FieldValueType;
  value: FieldValue | null;
  isSaving: boolean;
  /** Error returned by the API (shown under the inputs). */
  error: string | null;
  onSave: (value: FieldValue) => void;
  onCancel: () => void;
}

function InputControl({
  input,
  value,
  onChange,
}: {
  input: EditorInput;
  value: string;
  onChange: (value: string) => void;
}) {
  const common = {
    className: forms.control,
    value,
    onChange: (event: { target: { value: string } }) => onChange(event.target.value),
  };
  if (input.kind === 'textarea') return <textarea {...common} rows={3} />;
  return (
    <input {...common} type={input.kind} step={input.kind === 'number' ? '0.01' : undefined} />
  );
}

/** Generic editor: renders the inputs of the value type (`EDITOR_INPUTS`). */
export function FieldEditor({
  fieldLabel,
  type,
  value,
  isSaving,
  error,
  onSave,
  onCancel,
}: FieldEditorProps) {
  const [draft, setDraft] = useState(() => toDraft(value, type));
  const parsed = fromDraft(draft, type);

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (parsed !== null) onSave(parsed);
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit} aria-label={`Editar ${fieldLabel}`}>
      <div className={styles.inputs}>
        {EDITOR_INPUTS[type].map((input) => (
          <label key={input.key} className={forms.label}>
            <span>
              {input.label}
              {input.hint && <span className={forms.hint}> · {input.hint}</span>}
            </span>
            <InputControl
              input={input}
              value={draft[input.key] ?? ''}
              onChange={(text) => setDraft((current) => ({ ...current, [input.key]: text }))}
            />
          </label>
        ))}
      </div>
      {error && (
        <p className={styles.error} role="alert">
          {error}
        </p>
      )}
      <div className={styles.actions}>
        <Button type="submit" disabled={parsed === null || isSaving}>
          {isSaving ? 'Guardando…' : 'Guardar'}
        </Button>
        <Button variant="secondary" onClick={onCancel} disabled={isSaving}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}
