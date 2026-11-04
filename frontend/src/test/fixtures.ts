import type { AskResponse, DocumentDetail, DocumentSummary, ExtractedField } from '../api/types';

export function makeDocument(overrides: Partial<DocumentSummary> = {}): DocumentSummary {
  return {
    id: 'doc-1',
    filename: 'poliza_hogar.pdf',
    status: 'done',
    document_type: 'policy',
    page_count: 3,
    size_bytes: 120_000,
    error: null,
    created_at: '2026-11-04T10:00:00Z',
    updated_at: '2026-11-04T10:01:00Z',
    ...overrides,
  };
}

export function makeField(overrides: Partial<ExtractedField> = {}): ExtractedField {
  return {
    name: 'policy_number',
    value: 'FS-2024-001',
    confidence: 'high',
    status: 'ok',
    error: null,
    attempts: 1,
    page: 1,
    value_type: 'text',
    editable: true,
    original_value: null,
    edited_at: null,
    ...overrides,
  };
}

export function makeDetail(overrides: Partial<DocumentDetail> = {}): DocumentDetail {
  return { ...makeDocument(), chunk_count: 4, fields: [makeField()], ...overrides };
}

export function makeAnswer(overrides: Partial<AskResponse> = {}): AskResponse {
  return {
    conversation_id: 'conv-1',
    mode: 'answer',
    answer: 'La póliza cubre daños por agua [1].',
    answered: true,
    citations: [
      {
        marker: 1,
        document_id: 'doc-1',
        filename: 'informe_pericial.pdf',
        page: 2,
        excerpt: 'Daños por agua…',
      },
    ],
    ...overrides,
  };
}
