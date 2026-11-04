import { useMutation, useQueryClient } from '@tanstack/react-query';
import { documentsApi } from '../api/documents';
import type { FieldValue } from '../api/types';
import { queryKeys } from './queryKeys';

interface UpdateFieldInput {
  name: string;
  value: FieldValue;
}

/** `PATCH /documents/{id}/fields/{name}`. Refreshes the document detail. */
export function useUpdateField(documentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ name, value }: UpdateFieldInput) =>
      documentsApi.updateField(documentId, name, value),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.document(documentId) }),
  });
}
