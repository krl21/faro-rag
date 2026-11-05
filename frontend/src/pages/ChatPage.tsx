import { useEffect, useRef } from 'react';
import { Button } from '../components/Button';
import { ChatThread } from '../components/ChatThread';
import { DocumentSelect } from '../components/DocumentSelect';
import { EmptyState } from '../components/EmptyState';
import { PlusIcon } from '../components/icons/icons';
import { PageHeader } from '../components/PageHeader';
import { QuestionForm } from '../components/QuestionForm';
import { useChat } from '../hooks/useChat';
import { useDocuments } from '../hooks/useDocuments';
import { isQueryable } from '../lib/documentRules';
import styles from './ChatPage.module.css';

/** Smooth scrolling, unless the user asked the system for less motion. */
function scrollBehavior(): ScrollBehavior {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';
}

export function ChatPage() {
  const chat = useChat();
  const documents = useDocuments();
  // Only processed policies and invoices have fragments to search.
  const ready = (documents.data ?? []).filter(isQueryable);
  const hasDocument = chat.documentId !== null;

  // Keeps the last message (or the "searching" one) just above the question box.
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => {
    end.current?.scrollIntoView?.({ block: 'end', behavior: scrollBehavior() });
  }, [chat.messages.length, chat.isAsking]);

  return (
    <div className={styles.chat}>
      <PageHeader
        title="Preguntas"
        actions={
          <>
            <DocumentSelect
              label="Documento"
              documents={ready}
              value={chat.documentId}
              onChange={chat.selectDocument}
              placeholder={ready.length ? 'Elige un documento' : 'No hay documentos listos'}
            />
            <Button
              variant="secondary"
              icon={<PlusIcon size={18} />}
              onClick={chat.reset}
              disabled={chat.messages.length === 0 || chat.isAsking}
            >
              Nueva conversación
            </Button>
          </>
        }
      />

      <div className={styles.thread}>
        {chat.messages.length === 0 ? (
          <EmptyState>
            {hasDocument
              ? 'Pregunta lo que necesites sobre el documento elegido.'
              : 'Elige un documento para empezar a preguntar.'}
          </EmptyState>
        ) : (
          <ChatThread messages={chat.messages} isAsking={chat.isAsking} />
        )}
      </div>

      <div className={styles.composer}>
        <QuestionForm
          disabled={!hasDocument || chat.isAsking}
          placeholder={
            hasDocument ? 'Escribe tu pregunta…' : 'Elige un documento para poder preguntar'
          }
          onAsk={chat.ask}
        />
      </div>
      <div ref={end} />
    </div>
  );
}
