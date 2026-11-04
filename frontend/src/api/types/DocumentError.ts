/** Processing error of a document. */
export interface DocumentError {
  /** Machine-readable code, for example `no_extractable_text`. */
  code: string;
  message: string;
}
