import { screen, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { FieldsPage } from '../../pages/FieldsPage';
import { makeDetail, makeDocument, makeFact, makeField } from '../../test/fixtures';
import { renderWithProviders } from '../../test/render';
import { apiUrl, server } from '../../test/server';

const renderPage = (documentId: string | null) =>
  renderWithProviders(<FieldsPage documentId={documentId} onSelectDocument={() => {}} />);

describe('FieldsPage', () => {
  it('opens the most recent queryable document from the menu', async () => {
    server.use(
      http.get(apiUrl('/documents'), () =>
        HttpResponse.json([
          makeDocument({ id: 'other-1', filename: 'menu.pdf', document_type: 'unknown' }),
          makeDocument({ id: 'doc-1' }),
        ]),
      ),
      http.get(apiUrl('/documents/doc-1'), () => HttpResponse.json(makeDetail())),
    );
    renderPage(null);

    expect(await screen.findByText('FS-2024-001')).toBeInTheDocument();
  });

  it('explains that a document of type unknown has no fields', async () => {
    const other = { id: 'other-1', filename: 'menu.pdf', document_type: 'unknown' as const };
    server.use(
      http.get(apiUrl('/documents'), () => HttpResponse.json([makeDocument(other)])),
      http.get(apiUrl('/documents/other-1'), () =>
        HttpResponse.json(
          makeDetail({
            ...other,
            chunk_count: 0,
            fields: [makeField({ name: 'document_type', value: 'unknown', editable: false })],
          }),
        ),
      ),
    );
    renderPage('other-1');

    expect(await screen.findByText(/No es una póliza ni una factura/)).toBeInTheDocument();
    expect(screen.queryByText('Tipo de documento')).not.toBeInTheDocument();
  });

  it('lists the free data of the document under the fields', async () => {
    server.use(
      http.get(apiUrl('/documents'), () => HttpResponse.json([makeDocument()])),
      http.get(apiUrl('/documents/doc-1'), () =>
        HttpResponse.json(
          makeDetail({ facts: [makeFact({ label: 'N.º de bastidor', value: 'VF1' })] }),
        ),
      ),
    );
    renderPage('doc-1');

    const section = await screen.findByRole('region', { name: 'Otros datos' });
    expect(within(section).getByText('N.º de bastidor')).toBeInTheDocument();
    expect(within(section).getByText('VF1')).toBeInTheDocument();
    expect(screen.getByRole('list', { name: 'Campos' })).toHaveTextContent('Número de póliza');
  });
});
