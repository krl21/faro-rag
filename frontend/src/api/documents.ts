import type {
  AskResponse,
  DocumentAskRequest,
  DocumentDetail,
  DocumentSummary,
  DocumentUploadResponse,
  ExtractedField,
  FieldValue,
} from './types';
import { request } from './client';

const byId = (id: string) => `/documents/${encodeURIComponent(id)}`;

export const documentsApi = {
  list: () => request<DocumentSummary[]>('/documents'),

  get: (id: string) => request<DocumentDetail>(byId(id)),

  upload: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<DocumentUploadResponse>('/documents', { method: 'POST', body: form });
  },

  /** Replace a field value; the backend marks it as `edited`. */
  updateField: (id: string, fieldName: string, value: FieldValue) =>
    request<ExtractedField>(`${byId(id)}/fields/${encodeURIComponent(fieldName)}`, {
      method: 'PATCH',
      body: { value },
    }),

  /** Ask a question about one document. */
  ask: (id: string, body: DocumentAskRequest) =>
    request<AskResponse>(`${byId(id)}/ask`, { method: 'POST', body }),
};
