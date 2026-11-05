import { useState } from 'react';
import { Layout } from './components/Layout';
import type { View } from './lib/views';
import { ChatPage } from './pages/ChatPage';
import { DocumentsPage } from './pages/DocumentsPage';
import { FieldsPage } from './pages/FieldsPage';

/** Root: navigation only changes `view` and swaps the content, no page reload. */
export function App() {
  const [view, setView] = useState<View>('documents');
  const [fieldsDocumentId, setFieldsDocumentId] = useState<string | null>(null);

  const openFields = (id: string) => {
    setFieldsDocumentId(id);
    setView('fields');
  };

  return (
    <Layout view={view} onNavigate={setView}>
      {view === 'documents' && <DocumentsPage onOpenDocument={openFields} />}
      {view === 'chat' && <ChatPage />}
      {view === 'fields' && (
        <FieldsPage documentId={fieldsDocumentId} onSelectDocument={setFieldsDocumentId} />
      )}
    </Layout>
  );
}
