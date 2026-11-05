import { documentsApi } from '../api/documents';
import { useDocumentMutation } from './useDocumentMutation';

/** `DELETE /documents/{id}/fields/{name}`. */
export function useDeleteField(documentId: string) {
  return useDocumentMutation(documentId, (name: string) =>
    documentsApi.deleteField(documentId, name),
  );
}
