import { render } from '@testing-library/react';
import type { ReactElement } from 'react';
import { AppProviders } from '../AppProviders';
import { createQueryClient } from '../lib/queryClient';

/** Render inside the app providers with a fresh cache and no retries. */
export function renderWithProviders(ui: ReactElement) {
  const queryClient = createQueryClient();
  queryClient.setDefaultOptions({ queries: { retry: false }, mutations: { retry: false } });
  return render(<AppProviders queryClient={queryClient}>{ui}</AppProviders>);
}
