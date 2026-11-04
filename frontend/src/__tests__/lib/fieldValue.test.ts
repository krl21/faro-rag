import { draftError, formatFieldValue, fromDraft, toDraft } from '../../lib/fieldValue';
import { fieldDisplayStatus } from '../../lib/fieldState';
import { makeField } from '../../test/fixtures';

describe('field values', () => {
  it('formats each type for display', () => {
    expect(formatFieldValue({ start: '2024-01-01', end: '2024-12-31' }, 'period')).toBe(
      '01/01/2024 – 31/12/2024',
    );
    expect(formatFieldValue(['Incendio', 'Robo'], 'text_list')).toBe('Incendio, Robo');
  });

  it('translates coded values and leaves free text as is', () => {
    expect(formatFieldValue('policy', 'text', 'document_type')).toBe('Póliza');
    expect(formatFieldValue('invoice', 'text', 'document_type')).toBe('Factura');
    expect(formatFieldValue('policy', 'text', 'holder')).toBe('policy');
  });

  it('round-trips values through the editor draft', () => {
    const money = { amount: '1250.50', currency: 'EUR' };
    expect(fromDraft(toDraft(money, 'money'), 'money')).toEqual(money);
    expect(fromDraft(toDraft(['A', 'B'], 'text_list'), 'text_list')).toEqual(['A', 'B']);
  });

  it('returns null while a required input is empty', () => {
    expect(fromDraft(toDraft(null, 'period'), 'period')).toBeNull();
    expect(fromDraft({ start: '2024-01-01', end: '' }, 'period')).toBeNull();
  });

  it('explains the usual mistakes before saving', () => {
    expect(draftError({ start: '2024-12-31', end: '2024-01-01' }, 'period')).toMatch(/fin/);
    expect(draftError({ amount: '-5', currency: 'EUR' }, 'money')).toMatch(/importe/);
    expect(draftError({ amount: '5', currency: 'EURO' }, 'money')).toMatch(/moneda/);
    expect(draftError({ amount: '5', currency: 'eur' }, 'money')).toBeNull();
  });

  it('marks valid low-confidence values for review', () => {
    expect(fieldDisplayStatus(makeField({ confidence: 'low' }))).toBe('needs_review');
    expect(fieldDisplayStatus(makeField({ confidence: 'medium' }))).toBe('ok');
    expect(fieldDisplayStatus(makeField({ status: 'edited', confidence: 'low' }))).toBe('edited');
  });
});
