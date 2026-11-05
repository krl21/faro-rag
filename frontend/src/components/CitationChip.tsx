import type { Citation } from '../api/types';
import { formatPage } from '../lib/format';
import { fieldLabel } from '../lib/labels';
import styles from './CitationChip.module.css';

/** `informe_pericial.pdf` -> `informe_pericial`. */
function baseName(filename: string): string {
  return filename.replace(/\.pdf$/i, '');
}

/** What the citation points to, without the page. */
function citationOrigin(citation: Citation): string {
  if (citation.source === 'fragment') return baseName(citation.filename);
  // A fixed field has a Spanish label; a free one (table row, "label: value") only has the excerpt.
  return citation.field ? `Dato extraído: ${fieldLabel(citation.field)}` : 'Dato del documento';
}

/**
 * `informe_pericial · pág. 2` for a fragment, `Dato extraído: Fecha de la factura · pág. 1`
 * for a fixed field, `Dato del documento · pág. 1` for a free one. The page only shows
 * when the API knows it.
 */
function citationText(citation: Citation): string {
  const origin = citationOrigin(citation);
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
