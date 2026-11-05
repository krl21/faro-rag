import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { FactRow } from '../../components/FactRow';
import { makeDetail, makeFact } from '../../test/fixtures';
import { renderWithProviders } from '../../test/render';
import { apiUrl, server } from '../../test/server';

const FACT_URL = apiUrl('/documents/doc-1/facts/7');

const renderRow = (fact = makeFact()) =>
  renderWithProviders(
    <ul>
      <FactRow documentId="doc-1" fact={fact} />
    </ul>,
  );

describe('FactRow', () => {
  beforeEach(() => {
    server.use(http.get(apiUrl('/documents/doc-1'), () => HttpResponse.json(makeDetail())));
  });

  it('shows label, value, page and status', () => {
    renderRow();
    expect(screen.getByText('TOTAL FACTURA')).toBeInTheDocument();
    expect(screen.getByText('1.548,80 €')).toBeInTheDocument();
    expect(screen.getByText('pág. 1')).toBeInTheDocument();
    expect(screen.getByText('Correcto')).toBeInTheDocument();
  });

  it('shows a table row as its columns and the extracted value after an edit', () => {
    renderRow(
      makeFact({
        label: 'Kit',
        value: { Concepto: 'Kit', Cantidad: '2 ud' },
        status: 'edited',
        original_value: { label: 'Kit', value: { Concepto: 'Kit', Cantidad: '1 ud' } },
      }),
    );
    expect(screen.getByText('Concepto: Kit; Cantidad: 2 ud')).toBeInTheDocument();
    expect(screen.getByText('Modificado por el usuario')).toBeInTheDocument();
    expect(
      screen.getByText('Valor extraído: Kit: Concepto: Kit; Cantidad: 1 ud'),
    ).toBeInTheDocument();
  });

  it('sends the edited label and value', async () => {
    let body: unknown;
    server.use(
      http.patch(FACT_URL, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(makeFact({ status: 'edited' }));
      }),
    );
    renderRow();

    await userEvent.click(screen.getByRole('button', { name: 'Editar TOTAL FACTURA' }));
    const label = screen.getByRole('textbox', { name: 'Etiqueta' });
    await userEvent.clear(label);
    await userEvent.type(label, 'Total');
    const value = screen.getByRole('textbox', { name: 'Valor' });
    await userEvent.clear(value);
    await userEvent.type(value, '1.600,00 €');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));

    expect(body).toEqual({ label: 'Total', value: '1.600,00 €' });
    expect(await screen.findByRole('button', { name: 'Editar TOTAL FACTURA' })).toBeVisible();
  });

  it('edits the columns of a table row, adding and removing them', async () => {
    let body: unknown;
    server.use(
      http.patch(FACT_URL, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(makeFact());
      }),
    );
    renderRow(makeFact({ label: 'Kit', value: { Concepto: 'Kit', Cantidad: '1 ud' } }));

    await userEvent.click(screen.getByRole('button', { name: 'Editar Kit' }));
    await userEvent.click(screen.getByRole('button', { name: 'Quitar la columna 2' }));
    await userEvent.click(screen.getByRole('button', { name: 'Añadir columna' }));
    await userEvent.type(
      screen.getByRole('textbox', { name: 'Nombre de la columna 2' }),
      'Importe',
    );
    await userEvent.type(screen.getByRole('textbox', { name: 'Valor de la columna 2' }), '90 €');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));

    expect(body).toEqual({ label: 'Kit', value: { Concepto: 'Kit', Importe: '90 €' } });
  });

  it('shows the API validation error and keeps the editor open', async () => {
    server.use(
      http.patch(FACT_URL, () =>
        HttpResponse.json(
          { error: { code: 'invalid_fact_value', message: 'label too long' } },
          { status: 422 },
        ),
      ),
    );
    renderRow();

    await userEvent.click(screen.getByRole('button', { name: 'Editar TOTAL FACTURA' }));
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'La etiqueta o el valor no son válidos',
    );
    expect(screen.getByRole('form', { name: 'Editar TOTAL FACTURA' })).toBeInTheDocument();
  });

  it('deletes only after confirming in the row', async () => {
    let deleted = 0;
    server.use(
      http.delete(FACT_URL, () => {
        deleted += 1;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    renderRow();

    await userEvent.click(screen.getByRole('button', { name: 'Borrar TOTAL FACTURA' }));
    const confirm = screen.getByRole('group', { name: 'Confirmar borrado' });
    expect(confirm).toHaveTextContent('¿Borrar «TOTAL FACTURA»?');
    await userEvent.click(within(confirm).getByRole('button', { name: 'Cancelar' }));
    expect(deleted).toBe(0);

    await userEvent.click(screen.getByRole('button', { name: 'Borrar TOTAL FACTURA' }));
    await userEvent.click(screen.getByRole('button', { name: 'Borrar' }));
    await vi.waitFor(() => expect(deleted).toBe(1));
  });

  it('explains a failed deletion', async () => {
    server.use(
      http.delete(FACT_URL, () =>
        HttpResponse.json({ error: { code: 'fact_not_found', message: 'x' } }, { status: 404 }),
      ),
    );
    renderRow();

    await userEvent.click(screen.getByRole('button', { name: 'Borrar TOTAL FACTURA' }));
    await userEvent.click(screen.getByRole('button', { name: 'Borrar' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Este dato ya no existe.');
  });
});
