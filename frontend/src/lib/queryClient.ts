import { QueryClient } from '@tanstack/react-query';

/** Shared React Query client. Errors are shown in the UI, so one retry is enough. */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: 1, refetchOnWindowFocus: false },
      mutations: { retry: false },
    },
  });
}
