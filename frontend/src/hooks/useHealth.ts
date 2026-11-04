import { useQuery } from '@tanstack/react-query';
import { healthApi } from '../api/health';
import { config } from '../config';
import { queryKeys } from './queryKeys';

export type HealthState = 'checking' | 'ok' | 'degraded' | 'down';

const CHECKS = ['database', 'redis', 'worker'] as const;

/**
 * Health of the API and its dependencies, polled while the app is open.
 * `down`: the API does not answer; `degraded`: it answers but a dependency fails.
 */
export function useHealth(): { state: HealthState; failing: string[] } {
  const { data, isError, isPending } = useQuery({
    queryKey: queryKeys.health,
    queryFn: healthApi.ready,
    refetchInterval: config.healthPollMs,
    retry: false,
  });
  if (isPending) return { state: 'checking', failing: [] };
  if (isError || !data) return { state: 'down', failing: [] };
  const failing = CHECKS.filter((check) => data[check] === 'error');
  return { state: failing.length ? 'degraded' : 'ok', failing };
}
