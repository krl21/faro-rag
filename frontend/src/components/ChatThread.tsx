import type { AskResponse } from '../api/types';
import type { ChatMessage } from '../context/chatContext';
import { Banner } from './Banner';
import styles from './ChatThread.module.css';
import { CitationChip } from './CitationChip';
import { NoEvidenceMessage } from './NoEvidenceMessage';

function AssistantAnswer({ response }: { response: AskResponse }) {
  if (!response.answered) return <NoEvidenceMessage text={response.answer} />;
  return (
    <>
      <p className={styles.bubble}>{response.answer}</p>
      {response.citations.length > 0 && (
        <div className={styles.citations} aria-label="Citas">
          {response.citations.map((citation) => (
            <CitationChip key={citation.marker} citation={citation} />
          ))}
        </div>
      )}
    </>
  );
}

function MessageContent({ message }: { message: ChatMessage }) {
  switch (message.role) {
    case 'user':
      return <p className={styles.bubble}>{message.text}</p>;
    case 'assistant':
      return <AssistantAnswer response={message.response} />;
    case 'error':
      return <Banner tone="danger">{message.text}</Banner>;
  }
}

interface ChatThreadProps {
  messages: ChatMessage[];
  isAsking: boolean;
}

export function ChatThread({ messages, isAsking }: ChatThreadProps) {
  return (
    <ol className={styles.thread} aria-live="polite">
      {messages.map((message) => (
        <li
          key={message.id}
          className={`${styles.item} ${message.role === 'user' ? styles.user : styles.assistant}`}
        >
          <MessageContent message={message} />
        </li>
      ))}
      {isAsking && (
        <li className={`${styles.item} ${styles.assistant}`}>
          <p className={`${styles.bubble} ${styles.pending}`}>
            Buscando la información
            <span className={styles.dots} aria-hidden="true">
              <span>.</span>
              <span>.</span>
              <span>.</span>
            </span>
          </p>
        </li>
      )}
    </ol>
  );
}
