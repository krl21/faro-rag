import type { DocumentSummary } from '../api/types';
import { isOutOfScope } from '../lib/documentRules';
import { documentErrorMessage, OUT_OF_SCOPE_MESSAGE } from '../lib/errorMessages';
import { documentTypeLabel } from '../lib/labels';
import styles from './DocumentsTable.module.css';
import { StatusBadge } from './StatusBadge';

interface DocumentsTableProps {
  documents: DocumentSummary[];
  /** Opens the extracted fields of a document. */
  onOpen: (id: string) => void;
}

export function DocumentsTable({ documents, onOpen }: DocumentsTableProps) {
  return (
    <div className={styles.wrapper}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th scope="col">Documento</th>
            <th scope="col">Tipo</th>
            <th scope="col">Páginas</th>
            <th scope="col">Estado</th>
          </tr>
        </thead>
        <tbody>
          {documents.map((document) => (
            <tr key={document.id}>
              <td>
                <button
                  type="button"
                  className={styles.open}
                  onClick={() => onOpen(document.id)}
                  title="Ver campos extraídos"
                >
                  <span className={styles.filename}>{document.filename}</span>
                  {document.error && (
                    <span className={`${styles.subline} ${styles.error}`}>
                      {documentErrorMessage(document.error)}
                    </span>
                  )}
                  {isOutOfScope(document) && (
                    <span className={`${styles.subline} ${styles.note}`}>
                      {OUT_OF_SCOPE_MESSAGE}
                    </span>
                  )}
                </button>
              </td>
              <td className={styles.muted}>{documentTypeLabel(document.document_type)}</td>
              <td className={styles.muted}>{document.page_count ?? '—'}</td>
              <td>
                <StatusBadge status={document.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
