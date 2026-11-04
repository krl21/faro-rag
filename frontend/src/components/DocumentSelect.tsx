import { useId } from 'react';
import type { DocumentSummary } from '../api/types';
import forms from './forms.module.css';
import styles from './DocumentSelect.module.css';

interface DocumentSelectProps {
  documents: DocumentSummary[];
  value: string | null;
  onChange: (id: string | null) => void;
  label?: string;
  placeholder?: string;
}

/** Select one document. Used by the chat and the fields view. */
export function DocumentSelect({
  documents,
  value,
  onChange,
  label = 'Documento',
  placeholder = 'Elige un documento',
}: DocumentSelectProps) {
  const id = useId();
  return (
    <div className={forms.label}>
      <label htmlFor={id}>{label}</label>
      <select
        id={id}
        className={`${forms.control} ${styles.select}`}
        value={value ?? ''}
        onChange={(event) => onChange(event.target.value || null)}
      >
        <option value="" disabled>
          {placeholder}
        </option>
        {documents.map((document) => (
          <option key={document.id} value={document.id}>
            {document.filename}
          </option>
        ))}
      </select>
    </div>
  );
}
