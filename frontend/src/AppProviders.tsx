import { QueryClientProvider, type QueryClient } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';
import { ChatProvider } from './context/ChatProvider';
import { createQueryClient } from './lib/queryClient';

/** Every provider of the app; tests reuse it with their own client. */
export function AppProviders({
  children,
  queryClient,
}: {
  children: ReactNode;
  queryClient?: QueryClient;
}) {
  const [client] = useState(() => queryClient ?? createQueryClient());
  return (
    <QueryClientProvider client={client}>
      <ChatProvider>{children}</ChatProvider>
    </QueryClientProvider>
  );
}
