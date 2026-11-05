import type { Citation } from '../api/types';
import { formatPage } from '../lib/format';
import { fieldLabel } from '../lib/labels';
import styles from './CitationChip.module.css';

/** `informe_pericial.pdf` -> `informe_pericial`. */
function baseName(filename: string): string {
  return filename.replace(/\.pdf$/i, '');
}

/**
 * `informe_pericial · pág. 2` for a fragment, `Dato extraído: Fecha de la factura · pág. 1`
 * for a field. The page only shows when the API knows it.
 */
function citationText(citation: Citation): string {
  const origin =
    citation.source === 'field' && citation.field
      ? `Dato extraído: ${fieldLabel(citation.field)}`
      : baseName(citation.filename);
  return citation.page === null ? origin : `${origin} · ${formatPage(citation.page)}`;
}

/** Source of a statement: `[1] informe_pericial · pág. 2`; the excerpt shows on hover. */
export function CitationChip({ citation }: { citation: Citation }) {
  return (
    <span className={styles.chip} title={citation.excerpt}>
      <span className={styles.marker}>[{citation.marker}]</span>
      <span className={styles.name}>{citationText(citation)}</span>
    </span>
  );
}
