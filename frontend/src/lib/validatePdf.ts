import { formatBytes } from './format';

/**
 * Check type and size before uploading. It only improves the experience:
 * the API validates again (extension, MIME type and `%PDF-` signature).
 *
 * @returns A Spanish error message, or `null` when the file can be sent.
 */
export function validatePdf(file: File, maxBytes: number): string | null {
  const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
  if (!isPdf) return 'Solo se aceptan ficheros PDF.';
  if (file.size === 0) return 'El fichero está vacío.';
  if (file.size > maxBytes) {
    return `El PDF pesa ${formatBytes(file.size)} y el máximo es ${formatBytes(maxBytes)}.`;
  }
  return null;
}
