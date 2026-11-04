import type { DocumentDetail } from '../api/types';
import { Banner } from '../components/Banner';
import { DocumentSelect } from '../components/DocumentSelect';
import { EmptyState } from '../components/EmptyState';
import { FieldRow } from '../components/FieldRow';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { useDocument } from '../hooks/useDocument';
import { useDocuments } from '../hooks/useDocuments';
import { errorMessage, messageForCode } from '../lib/errorMessages';
import { documentTypeLabel } from '../lib/labels';
import { isActiveStatus } from '../lib/polling';
import styles from './Page.module.css';

function DocumentFields({ document }: { document: DocumentDetail }) {
  if (isActiveStatus(document.status)) {
    return (
      <Banner tone="info">
        El documento se está procesando. Los campos aparecerán aquí cuando termine.
      </Banner>
    );
  }
  if (document.status === 'failed') {
    return (
      <Banner tone="danger">
        No se pudo procesar el documento.{' '}
        {document.error && messageForCode(document.error.code, document.error.message)}
      </Banner>
    );
  }
  if (document.fields.length === 0) {
    return <EmptyState>Este documento no tiene campos extraídos.</EmptyState>;
  }
  return (
    <ul className={styles.list}>
      {document.fields.map((field) => (
        <FieldRow key={field.name} documentId={document.id} field={field} />
      ))}
    </ul>
  );
}

interface FieldsPageProps {
  /** Document chosen in the table; `null` when the view is opened from the menu. */
  documentId: string | null;
  onSelectDocument: (id: string | null) => void;
}

export function FieldsPage({ documentId, onSelectDocument }: FieldsPageProps) {
  const documents = useDocuments();
  const list = documents.data ?? [];
  // From the menu without a choice: the most recent processed document (the list is newest first).
  const selectedId = documentId ?? list.find((d) => d.status === 'done')?.id ?? null;
  const detail = useDocument(selectedId);
  const document = detail.data;

  return (
    <div className={styles.stack}>
      <PageHeader
        title="Campos extraídos"
        subtitle={
          document && (
            <>
              {document.filename} · {documentTypeLabel(document.document_type)}{' '}
              <StatusBadge status={document.status} />
            </>
          )
        }
        actions={<DocumentSelect documents={list} value={selectedId} onChange={onSelectDocument} />}
      />

      {selectedId === null ? (
        <EmptyState>
          {documents.isPending
            ? 'Cargando documentos…'
            : 'Elige un documento para ver sus campos extraídos.'}
        </EmptyState>
      ) : detail.isError ? (
        <Banner tone="danger">No se pudo cargar el documento. {errorMessage(detail.error)}</Banner>
      ) : !document ? (
        <p className={styles.muted}>Cargando campos…</p>
      ) : (
        <DocumentFields document={document} />
      )}
    </div>
  );
}
