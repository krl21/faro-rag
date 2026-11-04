import type { Citation } from './Citation';

/** Answer to a question. */
export interface AskResponse {
  /** Send it with the next question to continue the conversation. */
  conversation_id: string;
  mode: 'answer' | 'list';
  answer: string;
  /** `false` when there was not enough evidence to answer. */
  answered: boolean;
  citations: Citation[];
}
