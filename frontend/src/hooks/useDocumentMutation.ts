import { useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from './queryKeys';

/**
 * Mutation that changes a document's data (edit or delete a field or datum).
 * On success it refetches the document, so the view shows what the API stored.
 */
export function useDocumentMutation<TInput, TResult>(
  documentId: string,
  mutationFn: (input: TInput) => Promise<TResult>,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.document(documentId) }),
  });
}
