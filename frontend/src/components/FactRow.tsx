import type { DocumentFact } from '../api/types';
import { useDeleteFact } from '../hooks/useDeleteFact';
import { useUpdateFact } from '../hooks/useUpdateFact';
import { errorMessage } from '../lib/errorMessages';
import { formatFactValue } from '../lib/factValue';
import { formatPage } from '../lib/format';
import { DataRow } from './DataRow';
import { FactEditor } from './FactEditor';

interface FactRowProps {
  documentId: string;
  fact: DocumentFact;
}

/** A free datum (`label: value` line or table row): editable and deletable. */
export function FactRow({ documentId, fact }: FactRowProps) {
  const update = useUpdateFact(documentId);
  const remove = useDeleteFact(documentId);
  const original = fact.status === 'edited' ? fact.original_value : null;

  return (
    <DataRow
      label={fact.label}
      value={formatFactValue(fact.value)}
      original={original && `${original.label}: ${formatFactValue(original.value)}`}
      meta={fact.page ? formatPage(fact.page) : ''}
      status={fact.status}
      renderEditor={(close) => (
        <FactEditor
          label={fact.label}
          value={fact.value}
          isSaving={update.isPending}
          error={update.isError ? errorMessage(update.error) : null}
          onSave={(changes) =>
            update.mutate({ id: fact.id, update: changes }, { onSuccess: close })
          }
          onCancel={() => {
            update.reset();
            close();
          }}
        />
      )}
      deletion={{ run: () => remove.mutate(fact.id), state: remove }}
    />
  );
}
