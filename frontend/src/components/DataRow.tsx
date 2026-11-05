import { useState, type ReactNode } from 'react';
import { errorMessage } from '../lib/errorMessages';
import { STATUS_APPEARANCE, type BadgeStatus } from '../lib/statusAppearance';
import { Button } from './Button';
import styles from './DataRow.module.css';
import { EditIcon, TrashIcon } from './icons/icons';
import { StatusBadge } from './StatusBadge';

/** State of the delete request; a React Query mutation fits this shape. */
interface DeleteState {
  isPending: boolean;
  error: Error | null;
  reset: () => void;
}

interface DataRowProps {
  label: string;
  /** Formatted value; `null` shows "Sin valor". */
  value: string | null;
  /** Note under the value, in the row tone (for example, why it needs review). */
  note?: string | null;
  /** Value before the user edit, shown under the value. */
  original?: string | null;
  /** Page and confidence. */
  meta: string;
  status: BadgeStatus;
  /** Renders the editor; without it the row cannot be edited. */
  renderEditor?: (close: () => void) => ReactNode;
  /** Deletes the row; without it the row cannot be deleted. */
  deletion?: { run: () => void; state: DeleteState };
}

type Mode = 'view' | 'edit' | 'confirm-delete';

/** Row of a field or datum: value, origin, status, and editing and deletion in place. */
export function DataRow({
  label,
  value,
  note,
  original,
  meta,
  status,
  renderEditor,
  deletion,
}: DataRowProps) {
  const [mode, setMode] = useState<Mode>('view');
  const close = () => setMode('view');

  const cancelDelete = () => {
    deletion?.state.reset();
    close();
  };

  return (
    <li className={styles.row} data-tone={STATUS_APPEARANCE[status].tone}>
      <span className={styles.name}>{label}</span>
      <div className={styles.value}>
        {value === null ? <span className={styles.missing}>Sin valor</span> : value}
        {note && <p className={styles.note}>{note}</p>}
        {original && <p className={styles.original}>Valor extraído: {original}</p>}
      </div>
      <span className={styles.meta}>{meta}</span>
      <div className={styles.side}>
        <StatusBadge status={status} />
        {mode === 'view' && renderEditor && (
          <Button
            variant="ghost"
            icon={<EditIcon size={18} />}
            aria-label={`Editar ${label}`}
            title="Editar"
            onClick={() => setMode('edit')}
          />
        )}
        {mode === 'view' && deletion && (
          <Button
            variant="ghost"
            icon={<TrashIcon size={18} />}
            aria-label={`Borrar ${label}`}
            title="Borrar"
            onClick={() => setMode('confirm-delete')}
          />
        )}
      </div>
      {mode === 'edit' && renderEditor && <div className={styles.below}>{renderEditor(close)}</div>}
      {mode === 'confirm-delete' && deletion && (
        <div
          className={`${styles.below} ${styles.confirm}`}
          role="group"
          aria-label="Confirmar borrado"
        >
          <span>¿Borrar «{label}»? No se puede deshacer.</span>
          <div className={styles.confirmActions}>
            <Button variant="danger" onClick={deletion.run} disabled={deletion.state.isPending}>
              {deletion.state.isPending ? 'Borrando…' : 'Borrar'}
            </Button>
            <Button variant="secondary" onClick={cancelDelete} disabled={deletion.state.isPending}>
              Cancelar
            </Button>
          </div>
          {deletion.state.error && (
            <p className={styles.error} role="alert">
              {errorMessage(deletion.state.error)}
            </p>
          )}
        </div>
      )}
    </li>
  );
}
