/** Body of `POST /documents/{id}/ask`: a question about one document. */
export interface DocumentAskRequest {
  question: string;
  /** `null` starts a new conversation. */
  conversation_id: string | null;
}
