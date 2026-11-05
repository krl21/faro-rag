import { documentsApi } from '../api/documents';
import { useDocumentMutation } from './useDocumentMutation';

/** `DELETE /documents/{id}/facts/{fact_id}`. */
export function useDeleteFact(documentId: string) {
  return useDocumentMutation(documentId, (id: number) => documentsApi.deleteFact(documentId, id));
}
