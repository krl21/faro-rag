import { useRef, useState, type ChangeEvent } from 'react';
import type { DocumentSummary } from '../api/types';
import { Banner } from '../components/Banner';
import { Button } from '../components/Button';
import { DocumentsTable } from '../components/DocumentsTable';
import { EmptyState } from '../components/EmptyState';
import { UploadIcon } from '../components/icons/icons';
import { PageHeader } from '../components/PageHeader';
import { StatCard } from '../components/StatCard';
import { config } from '../config';
import { useDocuments } from '../hooks/useDocuments';
import { useUploadDocument } from '../hooks/useUploadDocument';
import { errorMessage } from '../lib/errorMessages';
import { isActiveStatus } from '../lib/polling';
import { validatePdf } from '../lib/validatePdf';
import styles from './Page.module.css';

interface Notice {
  tone: 'info' | 'danger';
  text: string;
}

function countStats(documents: DocumentSummary[]) {
  return {
    total: documents.length,
    done: documents.filter((d) => d.status === 'done').length,
    active: documents.filter((d) => isActiveStatus(d.status)).length,
    failed: documents.filter((d) => d.status === 'failed').length,
  };
}

interface DocumentsPageProps {
  onOpenDocument: (id: string) => void;
}

export function DocumentsPage({ onOpenDocument }: DocumentsPageProps) {
  const documents = useDocuments();
  const upload = useUploadDocument();
  const fileInput = useRef<HTMLInputElement>(null);
  const [notice, setNotice] = useState<Notice | null>(null);

  const handleFile = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = ''; // Allows choosing the same file again
    if (!file) return;

    const invalid = validatePdf(file, config.maxUploadBytes);
    if (invalid) {
      setNotice({ tone: 'danger', text: invalid });
      return;
    }
    setNotice(null);
    upload.mutate(file, {
      onSuccess: (result) => {
        if (result.duplicate) {
          setNotice({
            tone: 'info',
            text: `«${file.name}» ya estaba subido (mismo contenido). Se usa el documento existente.`,
          });
        }
      },
      onError: (error) =>
        setNotice({
          tone: 'danger',
          text: `No se pudo subir «${file.name}». ${errorMessage(error)}`,
        }),
    });
  };

  const list = documents.data ?? [];
  const stats = countStats(list);

  return (
    <div className={styles.stack}>
      <PageHeader
        title="Documentos"
        actions={
          <>
            <input
              ref={fileInput}
              type="file"
              accept="application/pdf,.pdf"
              className="visually-hidden"
              onChange={handleFile}
              aria-label="Seleccionar PDF"
              tabIndex={-1}
            />
            <Button
              icon={<UploadIcon size={18} />}
              onClick={() => fileInput.current?.click()}
              disabled={upload.isPending}
            >
              {upload.isPending ? 'Subiendo…' : 'Subir PDF'}
            </Button>
          </>
        }
      />

      {notice && (
        <Banner tone={notice.tone} onClose={() => setNotice(null)}>
          {notice.text}
        </Banner>
      )}
      {documents.isError && (
        <Banner tone="danger">
          No se pudo cargar la lista de documentos. {errorMessage(documents.error)}
        </Banner>
      )}

      <div className={styles.stats}>
        <StatCard label="Total" value={stats.total} tone="plain" />
        <StatCard label="Listos" value={stats.done} tone="success" />
        <StatCard label="En proceso" value={stats.active} tone="info" />
        <StatCard label="Con error" value={stats.failed} tone="danger" />
      </div>

      {documents.isPending ? (
        <p className={styles.muted}>Cargando documentos…</p>
      ) : list.length === 0 ? (
        <EmptyState>Todavía no hay documentos. Sube un PDF para empezar.</EmptyState>
      ) : (
        <DocumentsTable documents={list} onOpen={onOpenDocument} />
      )}
    </div>
  );
}
