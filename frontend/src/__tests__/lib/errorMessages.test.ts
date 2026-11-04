import { ApiError } from '../../api/ApiError';
import { documentErrorMessage, errorMessage, messageForCode } from '../../lib/errorMessages';

describe('error messages', () => {
  it('translates the known codes', () => {
    expect(messageForCode('no_extractable_text')).toBe('PDF escaneado sin texto extraíble.');
    expect(errorMessage(new ApiError(429, 'rate_limited', 'Rate limit exceeded'))).toMatch(
      /demasiadas preguntas/,
    );
  });

  it('explains that out-of-scope documents cannot be asked about', () => {
    const error = new ApiError(409, 'document_not_queryable', 'Document is not queryable');
    expect(errorMessage(error)).toMatch(/No es una póliza ni una factura/);
  });

  it('never shows HTTP statuses, codes or the API text', () => {
    const badGateway = errorMessage(new ApiError(502, 'unknown_error', 'HTTP 502'));
    expect(badGateway).toBe(
      'El servidor no está disponible en este momento. Inténtalo de nuevo en unos segundos.',
    );
    const unknown = errorMessage(new ApiError(500, 'brand_new_code', 'Something broke'));
    expect(unknown).not.toMatch(/500|brand_new_code|Something/);
    const invalid = errorMessage(new ApiError(422, 'validation_error', 'amount must be >= 0'));
    expect(invalid).not.toMatch(/amount/);
  });

  it('explains processing failures with unknown codes in Spanish', () => {
    expect(documentErrorMessage({ code: 'brand_new_code', message: 'Boom' })).toBe(
      'No se pudo procesar el documento.',
    );
  });
});
