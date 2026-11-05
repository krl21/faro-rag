import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { ChatPage } from '../../pages/ChatPage';
import { makeAnswer, makeDocument } from '../../test/fixtures';
import { renderWithProviders } from '../../test/render';
import { apiUrl, server } from '../../test/server';

const ASK_URL = apiUrl('/documents/doc-1/ask');

async function chooseDocumentAndAsk(question: string) {
  const select = await screen.findByRole('combobox', { name: 'Documento' });
  await screen.findByRole('option', { name: 'poliza_hogar.pdf' });
  await userEvent.selectOptions(select, 'doc-1');
  await userEvent.type(screen.getByRole('textbox', { name: 'Pregunta' }), question);
  await userEvent.click(screen.getByRole('button', { name: 'Enviar' }));
}

beforeEach(() => {
  server.use(
    http.get(apiUrl('/documents'), () =>
      HttpResponse.json([
        makeDocument(),
        makeDocument({ id: 'doc-2', filename: 'en_cola.pdf', status: 'pending' }),
        makeDocument({ id: 'doc-3', filename: 'menu.pdf', document_type: 'unknown' }),
      ]),
    ),
  );
});

describe('ChatPage', () => {
  it('only offers processed policies and invoices', async () => {
    renderWithProviders(<ChatPage />);
    await screen.findByRole('option', { name: 'poliza_hogar.pdf' });
    expect(screen.queryByRole('option', { name: 'en_cola.pdf' })).not.toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'menu.pdf' })).not.toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Pregunta' })).toBeDisabled();
  });

  it('shows the answer with its citations and continues the conversation', async () => {
    const bodies: unknown[] = [];
    server.use(
      http.post(ASK_URL, async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json(makeAnswer());
      }),
    );
    renderWithProviders(<ChatPage />);

    await chooseDocumentAndAsk('¿Qué cubre la póliza?');
    expect(await screen.findByText('La póliza cubre daños por agua [1].')).toBeInTheDocument();
    expect(screen.getByText('informe_pericial · pág. 2')).toBeInTheDocument();

    await userEvent.type(screen.getByRole('textbox', { name: 'Pregunta' }), '¿Y el robo?');
    await userEvent.click(screen.getByRole('button', { name: 'Enviar' }));
    await waitFor(() => expect(bodies).toHaveLength(2));

    expect(bodies).toEqual([
      { question: '¿Qué cubre la póliza?', conversation_id: null },
      { question: '¿Y el robo?', conversation_id: 'conv-1' },
    ]);
  });

  it('shows the refusal differently from an answer', async () => {
    server.use(
      http.post(ASK_URL, () =>
        HttpResponse.json(
          makeAnswer({
            answered: false,
            answer: 'No hay información suficiente para responder.',
            citations: [],
          }),
        ),
      ),
    );
    renderWithProviders(<ChatPage />);

    await chooseDocumentAndAsk('¿Cuál es la capital de Francia?');
    expect(await screen.findByRole('note', { name: 'Sin evidencia' })).toHaveTextContent(
      'No hay información suficiente para responder.',
    );
  });

  it('shows the rate limit instead of failing silently', async () => {
    server.use(
      http.post(ASK_URL, () =>
        HttpResponse.json(
          { error: { code: 'rate_limited', message: 'Rate limit exceeded: 10 per 1 minute' } },
          { status: 429 },
        ),
      ),
    );
    renderWithProviders(<ChatPage />);

    await chooseDocumentAndAsk('¿Qué cubre la póliza?');
    expect(await screen.findByRole('alert')).toHaveTextContent('demasiadas preguntas');
  });

  it('starts a new conversation without the previous history', async () => {
    const bodies: unknown[] = [];
    server.use(
      http.post(ASK_URL, async ({ request }) => {
        bodies.push(await request.json());
        return HttpResponse.json(makeAnswer());
      }),
    );
    renderWithProviders(<ChatPage />);

    await chooseDocumentAndAsk('Primera pregunta');
    await screen.findByText('La póliza cubre daños por agua [1].');
    await userEvent.click(screen.getByRole('button', { name: 'Nueva conversación' }));
    expect(screen.queryByText('Primera pregunta')).not.toBeInTheDocument();

    await userEvent.type(screen.getByRole('textbox', { name: 'Pregunta' }), 'Segunda pregunta');
    await userEvent.click(screen.getByRole('button', { name: 'Enviar' }));
    await waitFor(() => expect(bodies).toHaveLength(2));
    expect(bodies[1]).toEqual({ question: 'Segunda pregunta', conversation_id: null });
  });
});
