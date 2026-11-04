import { validatePdf } from '../../lib/validatePdf';

const MB = 1024 * 1024;
const file = (name: string, size: number, type = 'application/pdf') =>
  new File([new Uint8Array(size)], name, { type });

describe('validatePdf', () => {
  it('accepts a PDF within the limit', () => {
    expect(validatePdf(file('poliza.pdf', 1000), MB)).toBeNull();
  });

  it('rejects other types', () => {
    expect(validatePdf(file('foto.png', 1000, 'image/png'), MB)).toMatch(/Solo se aceptan/);
  });

  it('rejects empty and too large files', () => {
    expect(validatePdf(file('vacio.pdf', 0), MB)).toMatch(/vacío/);
    expect(validatePdf(file('grande.pdf', 2 * MB), MB)).toMatch(/máximo es 1,0 MB/);
  });
});
