import { useQuery } from '@tanstack/react-query';
import { documentsApi } from '../api/documents';
import { config } from '../config';
import { isActiveStatus, pollWhile } from '../lib/polling';
import { queryKeys } from './queryKeys';

/** `GET /documents/{id}`, polled only while that document is pending or processing. */
export function useDocument(id: string | null) {
  return useQuery({
    queryKey: queryKeys.document(id ?? ''),
    queryFn: () => documentsApi.get(id as string),
    enabled: id !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return pollWhile(status !== undefined && isActiveStatus(status), config.documentPollMs);
    },
  });
}
