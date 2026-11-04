import type { ReactNode } from 'react';
import styles from './Banner.module.css';
import { CloseIcon, InfoIcon, WarningIcon } from './icons/icons';

interface BannerProps {
  tone: 'info' | 'warning' | 'danger';
  children: ReactNode;
  /** Shows a close button when set. */
  onClose?: () => void;
}

/** Message that stays in the view until it is closed or its cause goes away. */
export function Banner({ tone, children, onClose }: BannerProps) {
  const Icon = tone === 'info' ? InfoIcon : WarningIcon;
  return (
    <div className={styles.banner} data-tone={tone} role={tone === 'danger' ? 'alert' : 'status'}>
      <Icon className={styles.icon} size={18} />
      <div className={styles.content}>{children}</div>
      {onClose && (
        <button type="button" className={styles.close} onClick={onClose} aria-label="Cerrar aviso">
          <CloseIcon size={16} />
        </button>
      )}
    </div>
  );
}
