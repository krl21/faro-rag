import { useState } from 'react';
import type { FactUpdate, FactValue } from '../api/types';
import {
  FACT_LABEL_MAX,
  FACT_MAX_COLUMNS,
  FACT_VALUE_MAX,
  factDraftError,
  fromFactDraft,
  toFactDraft,
  type ColumnDraft,
} from '../lib/factValue';
import { Button } from './Button';
import { EditorFrame } from './EditorFrame';
import styles from './FactEditor.module.css';
import forms from './forms.module.css';
import { CloseIcon, PlusIcon } from './icons/icons';

interface FactEditorProps {
  label: string;
  value: FactValue;
  isSaving: boolean;
  /** Error returned by the API (shown under the inputs). */
  error: string | null;
  onSave: (update: Required<FactUpdate>) => void;
  onCancel: () => void;
}

/** Columns of a table row: rename, change, add or remove them. */
function ColumnsEditor({
  columns,
  onChange,
}: {
  columns: ColumnDraft[];
  onChange: (columns: ColumnDraft[]) => void;
}) {
  const update = (index: number, patch: Partial<ColumnDraft>) =>
    onChange(columns.map((column, i) => (i === index ? { ...column, ...patch } : column)));

  return (
    <fieldset className={styles.columns}>
      <legend className={styles.legend}>Columnas de la fila</legend>
      {columns.map((column, index) => {
        const n = index + 1;
        return (
          <div key={index} className={styles.column}>
            <input
              className={forms.control}
              aria-label={`Nombre de la columna ${n}`}
              placeholder="Columna"
              value={column.name}
              onChange={(event) => update(index, { name: event.target.value })}
            />
            <input
              className={forms.control}
              aria-label={`Valor de la columna ${n}`}
              placeholder="Valor"
              value={column.value}
              maxLength={FACT_VALUE_MAX}
              onChange={(event) => update(index, { value: event.target.value })}
            />
            <Button
              variant="ghost"
              icon={<CloseIcon size={16} />}
              aria-label={`Quitar la columna ${n}`}
              title="Quitar columna"
              onClick={() => onChange(columns.filter((_, i) => i !== index))}
            />
          </div>
        );
      })}
      <Button
        variant="secondary"
        className={styles.add}
        icon={<PlusIcon size={16} />}
        disabled={columns.length >= FACT_MAX_COLUMNS}
        onClick={() => onChange([...columns, { name: '', value: '' }])}
      >
        Añadir columna
      </Button>
    </fieldset>
  );
}

/** Editor of a free datum: its label and its text, or the columns of its table row. */
export function FactEditor({ label, value, isSaving, error, onSave, onCancel }: FactEditorProps) {
  const [draft, setDraft] = useState(() => toFactDraft(label, value));
  const parsed = fromFactDraft(draft);

  return (
    <EditorFrame
      title={`Editar ${label}`}
      canSave={parsed !== null}
      isSaving={isSaving}
      message={factDraftError(draft) ?? error}
      onSave={() => parsed && onSave(parsed)}
      onCancel={onCancel}
    >
      <label className={forms.label}>
        Etiqueta
        <input
          className={forms.control}
          value={draft.label}
          maxLength={FACT_LABEL_MAX}
          onChange={(event) => setDraft({ ...draft, label: event.target.value })}
        />
      </label>
      {draft.kind === 'text' ? (
        <label className={forms.label}>
          Valor
          <textarea
            className={forms.control}
            rows={3}
            value={draft.text}
            maxLength={FACT_VALUE_MAX}
            onChange={(event) => setDraft({ ...draft, text: event.target.value })}
          />
        </label>
      ) : (
        <ColumnsEditor
          columns={draft.columns}
          onChange={(columns) => setDraft({ ...draft, columns })}
        />
      )}
    </EditorFrame>
  );
}
