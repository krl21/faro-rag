/** Where a citation comes from: a text fragment or an extracted field. */
export type CitationSource = 'fragment' | 'field';

/** A source supporting part of an answer. */
export interface Citation {
  /** Number used in the answer text (`[1]` -> `1`), from 1 in order of appearance. */
  marker: number;
  document_id: string;
  filename: string;
  source: CitationSource;
  /** Field name (`invoice_date`) when `source` is `field`; otherwise `null`. */
  field: string | null;
  /** 1-based page; `null` for a field whose page is unknown. */
  page: number | null;
  /** Fragment text, or `Label: value` for a field. */
  excerpt: string;
}
