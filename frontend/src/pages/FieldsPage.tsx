import type { DocumentDetail } from '../api/types';
import { Banner } from '../components/Banner';
import { DocumentSelect } from '../components/DocumentSelect';
import { EmptyState } from '../components/EmptyState';
import { FactRow } from '../components/FactRow';
import { FieldRow } from '../components/FieldRow';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { useDocument } from '../hooks/useDocument';
import { useDocuments } from '../hooks/useDocuments';
import { isOutOfScope, isProcessed, isQueryable } from '../lib/documentRules';
import { documentErrorMessage, errorMessage, OUT_OF_SCOPE_MESSAGE } from '../lib/errorMessages';
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
        No se pudo procesar el documento. {document.error && documentErrorMessage(document.error)}
      </Banner>
    );
  }
  if (isOutOfScope(document)) {
    return <Banner tone="info">{OUT_OF_SCOPE_MESSAGE}</Banner>;
  }
  if (document.fields.length === 0 && document.facts.length === 0) {
    return <EmptyState>Este documento no tiene campos extraídos.</EmptyState>;
  }
  return (
    <>
      {document.fields.length > 0 && (
        <ul className={styles.list} aria-label="Campos">
          {document.fields.map((field) => (
            <FieldRow key={field.name} documentId={document.id} field={field} />
          ))}
        </ul>
      )}
      {document.facts.length > 0 && (
        <section className={styles.section} aria-labelledby="facts-title">
          <h2 id="facts-title" className={styles.sectionTitle}>
            Otros datos
          </h2>
          <ul className={styles.list}>
            {document.facts.map((fact) => (
              <FactRow key={fact.id} documentId={document.id} fact={fact} />
            ))}
          </ul>
        </section>
      )}
    </>
  );
}

interface FieldsPageProps {
  /** Document chosen in the table; `null` when the view is opened from the menu. */
  documentId: string | null;
  onSelectDocument: (id: string | null) => void;
}

export function FieldsPage({ documentId, onSelectDocument }: FieldsPageProps) {
  const documents = useDocuments();
  // Only processed documents have something to show; `unknown` ones show the out-of-scope note.
  const list = (documents.data ?? []).filter(isProcessed);
  // From the menu without a choice: the most recent queryable document (the list is newest first).
  const selectedId = documentId ?? list.find(isQueryable)?.id ?? null;
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
