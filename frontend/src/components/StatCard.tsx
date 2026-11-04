import type { Tone } from '../lib/statusAppearance';
import styles from './StatCard.module.css';

interface StatCardProps {
  label: string;
  value: number;
  tone: Tone;
}

export function StatCard({ label, value, tone }: StatCardProps) {
  return (
    <div className={styles.card} data-tone={tone}>
      <p className={styles.label}>{label}</p>
      <p className={styles.value}>{value}</p>
    </div>
  );
}
