import type {
  AskResponse,
  DocumentAskRequest,
  DocumentDetail,
  DocumentSummary,
  DocumentUploadResponse,
  DocumentFact,
  ExtractedField,
  FactUpdate,
  FieldValue,
} from './types';
import { request } from './client';

const byId = (id: string) => `/documents/${encodeURIComponent(id)}`;
const fieldPath = (id: string, name: string) => `${byId(id)}/fields/${encodeURIComponent(name)}`;
const factPath = (id: string, factId: number) => `${byId(id)}/facts/${factId}`;

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
    request<ExtractedField>(fieldPath(id, fieldName), { method: 'PATCH', body: { value } }),

  /** Remove a fixed field: it disappears from `fields`. */
  deleteField: (id: string, fieldName: string) =>
    request<null>(fieldPath(id, fieldName), { method: 'DELETE' }),

  /** Change the label and/or value of a free datum; the backend marks it as `edited`. */
  updateFact: (id: string, factId: number, body: FactUpdate) =>
    request<DocumentFact>(factPath(id, factId), { method: 'PATCH', body }),

  /** Remove a free datum. */
  deleteFact: (id: string, factId: number) =>
    request<null>(factPath(id, factId), { method: 'DELETE' }),

  /** Ask a question about one document. */
  ask: (id: string, body: DocumentAskRequest) =>
    request<AskResponse>(`${byId(id)}/ask`, { method: 'POST', body }),
};
