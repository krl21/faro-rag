import { documentsApi } from '../api/documents';
import type { FactUpdate } from '../api/types';
import { useDocumentMutation } from './useDocumentMutation';

interface UpdateFactInput {
  id: number;
  update: FactUpdate;
}

/** `PATCH /documents/{id}/facts/{fact_id}`. */
export function useUpdateFact(documentId: string) {
  return useDocumentMutation(documentId, ({ id, update }: UpdateFactInput) =>
    documentsApi.updateFact(documentId, id, update),
  );
}
