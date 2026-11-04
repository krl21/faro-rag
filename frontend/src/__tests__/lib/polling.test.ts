import { hasActiveDocuments, isActiveStatus, pollWhile } from '../../lib/polling';
import { makeDocument } from '../../test/fixtures';

describe('polling rule', () => {
  it('treats only pending and processing as active', () => {
    expect(isActiveStatus('pending')).toBe(true);
    expect(isActiveStatus('processing')).toBe(true);
    expect(isActiveStatus('done')).toBe(false);
    expect(isActiveStatus('failed')).toBe(false);
  });

  it('polls while any document can still change', () => {
    const documents = [makeDocument({ status: 'done' }), makeDocument({ status: 'processing' })];
    expect(pollWhile(hasActiveDocuments(documents), 3000)).toBe(3000);
  });

  it('stops when every document is done or failed, or there is no data', () => {
    const documents = [makeDocument({ status: 'done' }), makeDocument({ status: 'failed' })];
    expect(pollWhile(hasActiveDocuments(documents), 3000)).toBe(false);
    expect(pollWhile(hasActiveDocuments(undefined), 3000)).toBe(false);
  });
});
