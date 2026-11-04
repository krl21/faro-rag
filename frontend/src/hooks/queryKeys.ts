/** React Query cache keys, in one place so invalidations cannot drift. */
export const queryKeys = {
  documents: ['documents'] as const,
  document: (id: string) => ['documents', id] as const,
  health: ['health'] as const,
};
