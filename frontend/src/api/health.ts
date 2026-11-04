import type { Readiness } from './types';
import { request } from './client';

export const healthApi = {
  /** 503 still carries the status of each dependency. */
  ready: () => request<Readiness>('/health/ready', { acceptStatuses: [503] }),
};
