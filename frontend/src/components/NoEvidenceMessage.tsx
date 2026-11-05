import { WarningIcon } from './icons/icons';
import styles from './NoEvidenceMessage.module.css';

/** Answer refused for lack of evidence: amber, so it is not mistaken for an answer. */
export function NoEvidenceMessage({ text }: { text: string }) {
  return (
    <div className={styles.message} data-tone="warning" role="note" aria-label="Sin evidencia">
      <WarningIcon className={styles.icon} size={18} />
      <p className={styles.text}>{text}</p>
    </div>
  );
}
