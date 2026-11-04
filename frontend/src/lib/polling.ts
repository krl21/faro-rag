import type { DocumentStatus, DocumentSummary } from '../api/types';

/** Statuses that can still change: only these justify polling. */
const ACTIVE_STATUSES: ReadonlySet<DocumentStatus> = new Set(['pending', 'processing']);

export function isActiveStatus(status: DocumentStatus): boolean {
  return ACTIVE_STATUSES.has(status);
}

export function hasActiveDocuments(documents: readonly DocumentSummary[] | undefined): boolean {
  return documents?.some((d) => isActiveStatus(d.status)) ?? false;
}

/**
 * Interval for React Query's `refetchInterval`: poll while `shouldPoll` is
 * true and stop (`false`) as soon as nothing can change any more.
 */
export function pollWhile(shouldPoll: boolean, intervalMs: number): number | false {
  return shouldPoll ? intervalMs : false;
}
