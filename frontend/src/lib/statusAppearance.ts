import type { DocumentStatus } from '../api/types';
import type { FieldDisplayStatus } from './fieldState';

export type BadgeStatus = DocumentStatus | FieldDisplayStatus;
/** Color role; maps to the `[data-tone]` rules of global.css. */
export type Tone = 'success' | 'info' | 'neutral' | 'warning' | 'danger' | 'plain';

/** Label and tone of every status, for documents and fields. */
export const STATUS_APPEARANCE: Record<BadgeStatus, { label: string; tone: Tone }> = {
  done: { label: 'Listo', tone: 'success' },
  processing: { label: 'Procesando', tone: 'info' },
  pending: { label: 'En cola', tone: 'neutral' },
  failed: { label: 'Fallido', tone: 'danger' },
  ok: { label: 'Correcto', tone: 'success' },
  needs_review: { label: 'Por revisar', tone: 'warning' },
  not_found: { label: 'No encontrado', tone: 'neutral' },
  edited: { label: 'Modificado por el usuario', tone: 'info' },
};
