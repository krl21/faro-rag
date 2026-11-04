/**
 * Status of an extracted field. `edited` means the user replaced the value.
 * `not_found` is not an error: the document does not contain the value.
 */
export type FieldStatus = 'ok' | 'not_found' | 'failed' | 'edited';
