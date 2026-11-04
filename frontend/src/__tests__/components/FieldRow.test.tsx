import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { FieldRow } from '../../components/FieldRow';
import { makeField } from '../../test/fixtures';
import { renderWithProviders } from '../../test/render';
import { apiUrl, server } from '../../test/server';

const renderRow = (field = makeField()) =>
  renderWithProviders(
    <ul>
      <FieldRow documentId="doc-1" field={field} />
    </ul>,
  );

describe('FieldRow', () => {
  it('shows value, source and status', () => {
    renderRow();
    expect(screen.getByText('Número de póliza')).toBeInTheDocument();
    expect(screen.getByText('FS-2024-001')).toBeInTheDocument();
    expect(screen.getByText('p. 1 · Confianza alta')).toBeInTheDocument();
    expect(screen.getByText('Correcto')).toBeInTheDocument();
  });

  it('warns about low confidence values', () => {
    renderRow(makeField({ confidence: 'low' }));
    expect(screen.getByText('Por revisar')).toBeInTheDocument();
    expect(screen.getByText('Confianza baja: revisa antes de usar')).toBeInTheDocument();
  });

  it('explains failed fields', () => {
    renderRow(
      makeField({
        name: 'invoice_amount',
        value_type: 'money',
        value: null,
        confidence: null,
        status: 'failed',
        attempts: 3,
        error: 'importe negativo',
      }),
    );
    expect(screen.getByText('Sin valor')).toBeInTheDocument();
    expect(
      screen.getByText('Validación fallida tras 2 reintentos: importe negativo'),
    ).toBeInTheDocument();
  });

  it('does not offer editing for read-only fields', () => {
    renderRow(makeField({ name: 'document_type', value: 'policy', editable: false }));
    expect(screen.getByText('Póliza')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Editar/ })).not.toBeInTheDocument();
  });

  it('shows the extracted value after an edit', () => {
    renderRow(makeField({ status: 'edited', confidence: null, original_value: 'FS-OLD' }));
    expect(screen.getByText('Modificado por el usuario')).toBeInTheDocument();
    expect(screen.getByText('Valor extraído: FS-OLD')).toBeInTheDocument();
  });

  it('sends the edited value to the API', async () => {
    let body: unknown;
    server.use(
      http.patch(apiUrl('/documents/doc-1/fields/policy_number'), async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(makeField({ value: 'FS-9', status: 'edited' }));
      }),
      http.get(apiUrl('/documents/doc-1'), () => HttpResponse.json({})),
    );
    renderRow();

    await userEvent.click(screen.getByRole('button', { name: 'Editar Número de póliza' }));
    const input = screen.getByRole('textbox');
    await userEvent.clear(input);
    await userEvent.type(input, 'FS-9');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));

    expect(body).toEqual({ value: 'FS-9' });
    expect(await screen.findByRole('button', { name: 'Editar Número de póliza' })).toBeVisible();
  });

  it('shows the API validation error and keeps the editor open', async () => {
    server.use(
      http.patch(apiUrl('/documents/doc-1/fields/policy_number'), () =>
        HttpResponse.json(
          { error: { code: 'invalid_field_value', message: "Invalid value for 'policy_number'" } },
          { status: 422 },
        ),
      ),
    );
    renderRow();

    await userEvent.click(screen.getByRole('button', { name: 'Editar Número de póliza' }));
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      "El valor no es válido. Invalid value for 'policy_number'",
    );
  });
});
