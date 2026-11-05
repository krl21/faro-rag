import { render, screen } from '@testing-library/react';
import type { Citation } from '../../api/types';
import { CitationChip } from '../../components/CitationChip';

const fragment: Citation = {
  marker: 1,
  document_id: 'doc-1',
  filename: 'factura.pdf',
  source: 'fragment',
  field: null,
  page: 2,
  excerpt: 'Total a pagar…',
};

describe('CitationChip', () => {
  it('shows the file and page of a fragment', () => {
    render(<CitationChip citation={fragment} />);
    expect(screen.getByText('factura · pág. 2')).toBeInTheDocument();
  });

  it('shows an extracted field by its label, with the excerpt on hover', () => {
    const field: Citation = {
      ...fragment,
      source: 'field',
      field: 'invoice_date',
      page: 1,
      excerpt: 'Fecha de emisión de la factura: 2026-04-22',
    };
    render(<CitationChip citation={field} />);
    const text = screen.getByText('Dato extraído: Fecha de la factura · pág. 1');
    expect(text.parentElement).toHaveAttribute('title', field.excerpt);
  });

  it('omits the page when it is unknown', () => {
    render(
      <CitationChip citation={{ ...fragment, source: 'field', field: 'holder', page: null }} />,
    );
    expect(screen.getByText('Dato extraído: Titular')).toBeInTheDocument();
  });
});
