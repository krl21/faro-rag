import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import type * as ConfigModule from '../../config';
import { DocumentsPage } from '../../pages/DocumentsPage';
import { makeDocument } from '../../test/fixtures';
import { renderWithProviders } from '../../test/render';
import { apiUrl, server } from '../../test/server';

// Short interval so the polling test runs in real time.
vi.mock('../../config', async (importOriginal) => {
  const { config } = await importOriginal<typeof ConfigModule>();
  return { config: { ...config, documentPollMs: 30, maxUploadBytes: 1024 } };
});

const pdf = (name = 'poliza.pdf', size = 100) =>
  new File([new Uint8Array(size)], name, { type: 'application/pdf' });

const renderPage = () => renderWithProviders(<DocumentsPage onOpenDocument={() => {}} />);

describe('DocumentsPage', () => {
  it('shows counters, statuses and the reason of a failure', async () => {
    server.use(
      http.get(apiUrl('/documents'), () =>
        HttpResponse.json([
          makeDocument({ id: '1', filename: 'a.pdf', status: 'done' }),
          makeDocument({
            id: '2',
            filename: 'escaneado.pdf',
            status: 'failed',
            error: { code: 'no_extractable_text', message: 'No text' },
          }),
          makeDocument({ id: '3', filename: 'menu.pdf', document_type: 'unknown' }),
        ]),
      ),
    );
    renderPage();

    expect(await screen.findByText('escaneado.pdf')).toBeInTheDocument();
    expect(screen.getByText('PDF escaneado sin texto extraíble.')).toBeInTheDocument();
    expect(screen.getByText(/No es una póliza ni una factura/)).toBeInTheDocument();
    expect(screen.getByText('Total').nextSibling).toHaveTextContent('3');
    expect(screen.getByText('Con error').nextSibling).toHaveTextContent('1');
    // Only processed documents (also `unknown` ones) open the fields view.
    expect(screen.getByRole('button', { name: 'a.pdf' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /menu\.pdf/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /escaneado\.pdf/ })).not.toBeInTheDocument();
  });

  it('polls while a document is processing and stops when it is done', async () => {
    let calls = 0;
    server.use(
      http.get(apiUrl('/documents'), () => {
        calls += 1;
        const status = calls < 3 ? 'processing' : 'done';
        return HttpResponse.json([makeDocument({ status })]);
      }),
    );
    renderPage();

    expect(await screen.findByText('Procesando')).toBeInTheDocument();
    expect(await screen.findByText('Listo')).toBeInTheDocument();
    const callsWhenDone = calls;
    await new Promise((resolve) => setTimeout(resolve, 150));
    expect(calls).toBe(callsWhenDone);
  });

  it('validates the file before uploading', async () => {
    server.use(http.get(apiUrl('/documents'), () => HttpResponse.json([])));
    renderPage();

    await userEvent.upload(screen.getByLabelText('Seleccionar PDF'), pdf('grande.pdf', 4096));
    expect(await screen.findByRole('alert')).toHaveTextContent('El PDF pesa 4 KB');
  });

  it('uploads a PDF and reports duplicates in a banner', async () => {
    server.use(
      http.get(apiUrl('/documents'), () => HttpResponse.json([])),
      http.post(apiUrl('/documents'), () =>
        HttpResponse.json({ id: 'doc-1', status: 'done', duplicate: true, message: 'exists' }),
      ),
    );
    renderPage();

    await userEvent.upload(screen.getByLabelText('Seleccionar PDF'), pdf());
    expect(await screen.findByRole('alert')).toHaveTextContent('«poliza.pdf» ya está almacenado');
  });

  it('shows the API error when the upload is rejected', async () => {
    server.use(
      http.get(apiUrl('/documents'), () => HttpResponse.json([])),
      http.post(apiUrl('/documents'), () =>
        HttpResponse.json(
          { error: { code: 'invalid_file_type', message: 'The file content is not a PDF' } },
          { status: 415 },
        ),
      ),
    );
    renderPage();

    await userEvent.upload(screen.getByLabelText('Seleccionar PDF'), pdf());
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('El fichero no es un PDF válido.'),
    );
  });
});
