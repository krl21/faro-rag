import { useMutation, useQueryClient } from '@tanstack/react-query';
import { documentsApi } from '../api/documents';
import { queryKeys } from './queryKeys';

/** `POST /documents`. Refreshes the list, which turns polling on for the new document. */
export function useUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: documentsApi.upload,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.documents }),
  });
}
