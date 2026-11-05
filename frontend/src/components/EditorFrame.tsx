import type { FormEvent, ReactNode } from 'react';
import { Button } from './Button';
import styles from './EditorFrame.module.css';

interface EditorFrameProps {
  /** Accessible name of the form (`Editar Titular`). */
  title: string;
  /** Whether the inputs hold a valid value. */
  canSave: boolean;
  isSaving: boolean;
  /** Problem to show under the inputs: the local check first, then the API error. */
  message: string | null;
  onSave: () => void;
  onCancel: () => void;
  children: ReactNode;
}

/** Form shared by the editors: inputs, problem and Guardar/Cancelar. */
export function EditorFrame({
  title,
  canSave,
  isSaving,
  message,
  onSave,
  onCancel,
  children,
}: EditorFrameProps) {
  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (canSave) onSave();
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit} aria-label={title}>
      {children}
      {message && (
        <p className={styles.error} role="alert">
          {message}
        </p>
      )}
      <div className={styles.actions}>
        <Button type="submit" disabled={!canSave || isSaving}>
          {isSaving ? 'Guardando…' : 'Guardar'}
        </Button>
        <Button variant="secondary" onClick={onCancel} disabled={isSaving}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}
