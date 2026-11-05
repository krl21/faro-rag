import { isOutOfScope, isProcessed, isQueryable } from '../../lib/documentRules';

describe('document rules', () => {
  it('treats only done documents as processed', () => {
    expect(isProcessed({ status: 'done' })).toBe(true);
    expect(isProcessed({ status: 'pending' })).toBe(false);
    expect(isProcessed({ status: 'processing' })).toBe(false);
    expect(isProcessed({ status: 'failed' })).toBe(false);
  });

  it('allows questions only on processed policies and invoices', () => {
    expect(isQueryable({ status: 'done', document_type: 'policy' })).toBe(true);
    expect(isQueryable({ status: 'done', document_type: 'invoice' })).toBe(true);
    expect(isQueryable({ status: 'done', document_type: 'unknown' })).toBe(false);
    expect(isQueryable({ status: 'processing', document_type: 'policy' })).toBe(false);
  });

  it('marks processed documents of type unknown as out of scope', () => {
    expect(isOutOfScope({ status: 'done', document_type: 'unknown' })).toBe(true);
    expect(isOutOfScope({ status: 'failed', document_type: 'unknown' })).toBe(false);
  });
});
