/** A source supporting part of an answer. */
export interface Citation {
  /** Number used in the answer text (`[1]` -> `1`). */
  marker: number;
  document_id: string;
  filename: string;
  /** 1-based page. */
  page: number;
  excerpt: string;
}
