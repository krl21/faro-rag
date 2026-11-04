import { ApiError } from '../../api/ApiError';
import { errorMessage, messageForCode } from '../../lib/errorMessages';

describe('error messages', () => {
  it('translates the known codes', () => {
    expect(messageForCode('no_extractable_text')).toBe('PDF escaneado sin texto extraíble.');
    expect(errorMessage(new ApiError(429, 'rate_limited', 'Rate limit exceeded'))).toMatch(
      /demasiadas preguntas/,
    );
  });

  it('falls back to the API message for unknown codes', () => {
    expect(messageForCode('brand_new_code', 'Something new')).toBe('Something new');
  });

  it('keeps the detail of validation errors', () => {
    const error = new ApiError(422, 'validation_error', 'amount must be >= 0');
    expect(errorMessage(error)).toBe('Datos no válidos. amount must be >= 0');
  });
});
