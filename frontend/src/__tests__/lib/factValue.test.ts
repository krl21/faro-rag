import {
  factDraftError,
  formatFactValue,
  fromFactDraft,
  toFactDraft,
  type FactDraft,
} from '../../lib/factValue';

const row = { 'Kit de estanterías': 'Kit de estanterías', Cantidad: '1 ud', Importe: '1.280,00 €' };

describe('formatFactValue', () => {
  it('shows text as is and a table row as its columns, in order', () => {
    expect(formatFactValue('1.548,80 €')).toBe('1.548,80 €');
    expect(formatFactValue(row)).toBe(
      'Kit de estanterías: Kit de estanterías; Cantidad: 1 ud; Importe: 1.280,00 €',
    );
  });
});

describe('fact editor draft', () => {
  it('round-trips text and table rows, always sending the label', () => {
    expect(fromFactDraft(toFactDraft(' TOTAL ', ' 10 € '))).toEqual({
      label: 'TOTAL',
      value: '10 €',
    });
    expect(fromFactDraft(toFactDraft('Kit', row))).toEqual({ label: 'Kit', value: row });
  });

  it('drops empty cells, like the API', () => {
    const draft: FactDraft = {
      kind: 'row',
      label: 'Kit',
      columns: [
        { name: 'Cantidad', value: '2 ud' },
        { name: 'Notas', value: '  ' },
      ],
    };
    expect(fromFactDraft(draft)).toEqual({ label: 'Kit', value: { Cantidad: '2 ud' } });
  });

  it('explains the usual mistakes before saving', () => {
    const text = (label: string, value: string): FactDraft => ({
      kind: 'text',
      label,
      text: value,
    });
    const columns = (...list: [string, string][]): FactDraft => ({
      kind: 'row',
      label: 'Kit',
      columns: list.map(([name, value]) => ({ name, value })),
    });

    expect(factDraftError(text(' ', 'x'))).toBe('La etiqueta no puede estar vacía.');
    expect(factDraftError(text('x'.repeat(61), 'x'))).toMatch(/como máximo 60/);
    expect(factDraftError(text('Total', ''))).toBe('El valor no puede estar vacío.');
    expect(factDraftError(text('Total', 'x'.repeat(301)))).toMatch(/como máximo 300/);
    expect(factDraftError(columns(['Cantidad', '']))).toMatch(/al menos una columna/);
    expect(factDraftError(columns(['', '1 ud']))).toMatch(/necesita un nombre/);
    expect(factDraftError(columns(['A', '1'], ['A', '2']))).toMatch(/mismo nombre/);
    expect(factDraftError(columns(['Cantidad', '1 ud']))).toBeNull();
    expect(fromFactDraft(text('', 'x'))).toBeNull();
  });
});
