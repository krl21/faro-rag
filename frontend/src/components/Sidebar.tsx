import type { ReactNode } from 'react';
import type { View } from '../lib/views';
import { HealthIndicator } from './HealthIndicator';
import { ChatIcon, DocumentIcon, FieldsIcon, LighthouseIcon } from './icons/icons';
import { NavItem } from './NavItem';
import styles from './Sidebar.module.css';

const NAV_ITEMS: { view: View; label: string; icon: ReactNode }[] = [
  { view: 'documents', label: 'Documentos', icon: <DocumentIcon /> },
  { view: 'chat', label: 'Preguntas', icon: <ChatIcon /> },
  { view: 'fields', label: 'Campos extraídos', icon: <FieldsIcon /> },
];

interface SidebarProps {
  view: View;
  onNavigate: (view: View) => void;
}

export function Sidebar({ view, onNavigate }: SidebarProps) {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.brand}>
        <LighthouseIcon size={28} />
        <span className={styles.name}>Faro RAG</span>
      </div>
      <nav className={styles.nav} aria-label="Vistas">
        {NAV_ITEMS.map((item) => (
          <NavItem
            key={item.view}
            label={item.label}
            icon={item.icon}
            active={item.view === view}
            onClick={() => onNavigate(item.view)}
          />
        ))}
      </nav>
      <div className={styles.footer}>
        <HealthIndicator />
      </div>
    </aside>
  );
}
