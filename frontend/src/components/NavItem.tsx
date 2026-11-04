import type { ReactNode } from 'react';
import styles from './NavItem.module.css';

interface NavItemProps {
  label: string;
  icon: ReactNode;
  active: boolean;
  onClick: () => void;
}

export function NavItem({ label, icon, active, onClick }: NavItemProps) {
  return (
    <button
      type="button"
      className={active ? `${styles.item} ${styles.active}` : styles.item}
      aria-current={active ? 'page' : undefined}
      onClick={onClick}
    >
      {icon}
      {label}
    </button>
  );
}
