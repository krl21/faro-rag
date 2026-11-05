import { documentsApi } from '../api/documents';
import type { FieldValue } from '../api/types';
import { useDocumentMutation } from './useDocumentMutation';

interface UpdateFieldInput {
  name: string;
  value: FieldValue;
}

/** `PATCH /documents/{id}/fields/{name}`. */
export function useUpdateField(documentId: string) {
  return useDocumentMutation(documentId, ({ name, value }: UpdateFieldInput) =>
    documentsApi.updateField(documentId, name, value),
  );
}
