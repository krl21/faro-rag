import { createContext } from 'react';
import type { AskResponse } from '../api/types';

export type ChatMessage =
  | { id: number; role: 'user'; text: string }
  | { id: number; role: 'assistant'; response: AskResponse }
  | { id: number; role: 'error'; text: string };

/** A message before it gets its id (`Omit` applied to each variant of the union). */
export type NewChatMessage = ChatMessage extends infer M
  ? M extends ChatMessage
    ? Omit<M, 'id'>
    : never
  : never;

export interface ChatState {
  /** Document the questions are about. Required to ask. */
  documentId: string | null;
  messages: ChatMessage[];
  /** `null` until the first answer creates the conversation in the backend. */
  conversationId: string | null;
  isAsking: boolean;
  selectDocument: (id: string | null) => void;
  ask: (question: string) => Promise<void>;
  /** "Nueva conversación": clears the UI history; the backend keeps it stored. */
  reset: () => void;
}

export const ChatContext = createContext<ChatState | null>(null);
