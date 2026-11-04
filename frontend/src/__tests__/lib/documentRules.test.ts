import { isOutOfScope, isQueryable } from '../../lib/documentRules';

describe('document rules', () => {
  it('allows questions only on processed policies and invoices', () => {
    expect(isQueryable({ status: 'done', document_type: 'policy' })).toBe(true);
    expect(isQueryable({ status: 'done', document_type: 'invoice' })).toBe(true);
    expect(isQueryable({ status: 'done', document_type: 'other' })).toBe(false);
    expect(isQueryable({ status: 'processing', document_type: 'policy' })).toBe(false);
  });

  it('marks processed documents of type other as out of scope', () => {
    expect(isOutOfScope({ status: 'done', document_type: 'other' })).toBe(true);
    expect(isOutOfScope({ status: 'failed', document_type: 'other' })).toBe(false);
  });
});
