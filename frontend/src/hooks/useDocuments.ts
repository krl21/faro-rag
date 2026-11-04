import { useQuery } from '@tanstack/react-query';
import { documentsApi } from '../api/documents';
import { config } from '../config';
import { hasActiveDocuments, pollWhile } from '../lib/polling';
import { queryKeys } from './queryKeys';

/**
 * `GET /documents`, polled only while some document is pending or processing.
 * Polling restarts by itself when an upload invalidates the list.
 */
export function useDocuments() {
  return useQuery({
    queryKey: queryKeys.documents,
    queryFn: documentsApi.list,
    refetchInterval: (query) =>
      pollWhile(hasActiveDocuments(query.state.data), config.documentPollMs),
  });
}
