import { useHealth, type HealthState } from '../hooks/useHealth';
import type { Tone } from '../lib/statusAppearance';
import styles from './HealthIndicator.module.css';

const CHECK_LABELS: Record<string, string> = {
  database: 'base de datos',
  redis: 'cola',
  worker: 'worker',
};

const APPEARANCE: Record<HealthState, { tone: Tone; label: string }> = {
  checking: { tone: 'neutral', label: 'Comprobando estado…' },
  ok: { tone: 'success', label: 'API y worker activos' },
  degraded: { tone: 'warning', label: 'Fallo en' },
  down: { tone: 'danger', label: 'API no disponible' },
};

export function HealthIndicator() {
  const { state, failing } = useHealth();
  const { tone, label } = APPEARANCE[state];
  const text =
    state === 'degraded'
      ? `${label}: ${failing.map((c) => CHECK_LABELS[c] ?? c).join(', ')}`
      : label;
  return (
    <div className={styles.health} role="status" data-tone={tone}>
      <span className={styles.dot} aria-hidden="true" />
      {text}
    </div>
  );
}
