import { STATUS_APPEARANCE, type BadgeStatus } from '../lib/statusAppearance';
import styles from './StatusBadge.module.css';

export function StatusBadge({ status }: { status: BadgeStatus }) {
  const { label, tone } = STATUS_APPEARANCE[status];
  return (
    <span className={styles.badge} data-tone={tone}>
      <span className={styles.dot} aria-hidden="true" />
      {label}
    </span>
  );
}
