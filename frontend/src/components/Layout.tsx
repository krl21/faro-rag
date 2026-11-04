import type { ReactNode } from 'react';
import type { View } from '../lib/views';
import styles from './Layout.module.css';
import { Sidebar } from './Sidebar';

interface LayoutProps {
  view: View;
  onNavigate: (view: View) => void;
  children: ReactNode;
}

export function Layout({ view, onNavigate, children }: LayoutProps) {
  return (
    <div className={styles.layout}>
      <Sidebar view={view} onNavigate={onNavigate} />
      <main className={styles.main}>{children}</main>
    </div>
  );
}
