import { useCallback, useMemo, useRef, useState, type ReactNode } from 'react';
import { documentsApi } from '../api/documents';
import { errorMessage } from '../lib/errorMessages';
import { ChatContext, type ChatMessage, type ChatState, type NewChatMessage } from './chatContext';

/**
 * Keeps the conversation above the views, so switching views does not lose it.
 * The first question goes with `conversation_id: null`; the backend creates the
 * conversation and its id travels with every later question until `reset`.
 */
export function ChatProvider({ children }: { children: ReactNode }) {
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isAsking, setIsAsking] = useState(false);
  const nextId = useRef(0);

  const append = useCallback((message: NewChatMessage) => {
    const id = nextId.current++;
    setMessages((current) => [...current, { ...message, id } as ChatMessage]);
  }, []);

  const ask = useCallback(
    async (question: string) => {
      if (!documentId) return;
      append({ role: 'user', text: question });
      setIsAsking(true);
      try {
        const response = await documentsApi.ask(documentId, {
          question,
          conversation_id: conversationId,
        });
        setConversationId(response.conversation_id);
        append({ role: 'assistant', response });
      } catch (error) {
        append({ role: 'error', text: errorMessage(error) });
      } finally {
        setIsAsking(false);
      }
    },
    [append, conversationId, documentId],
  );

  const reset = useCallback(() => {
    setMessages([]);
    setConversationId(null);
  }, []);

  const value = useMemo<ChatState>(
    () => ({
      documentId,
      messages,
      conversationId,
      isAsking,
      selectDocument: setDocumentId,
      ask,
      reset,
    }),
    [documentId, messages, conversationId, isAsking, ask, reset],
  );

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}
