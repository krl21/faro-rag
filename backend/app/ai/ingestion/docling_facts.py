"""Label-value data of a Docling document: its tables and its "campo: valor" lines."""

from collections import defaultdict
from typing import Any

from app.ai.ingestion.fact_parsing import dedupe, facts_from_grid, facts_from_lines
from app.domain.dtos import FactDraft

# Most data a document can give; the rest is ignored (it stays in the text).
MAX_FACTS = 300
# Docling labels of text items that are not page content.
_SKIPPED_LABELS = frozenset({"page_footer", "page_header", "picture", "formula", "code"})
_HEADER_LABEL = "Encabezado del documento"


def facts_from_docling(document: Any) -> list[FactDraft]:
    """Find the data of a converted document.

    Tables are read cell by cell (vertical, horizontal or records, see
    ``fact_parsing``). Text outside tables is read line by line, in reading
    order, page by page. The page header (issuer name, address, tax id...) is
    not in the Markdown text, so it is kept once as a datum.

    Args:
        document: ``DoclingDocument`` returned by the converter.

    Returns:
        Up to ``MAX_FACTS`` data, in document order.
    """
    facts: list[FactDraft] = []
    for index, table in enumerate(document.tables):
        grid = table.data.grid
        if not grid:
            continue
        facts += facts_from_grid(
            [[cell.text for cell in row] for row in grid],
            page=_page(table),
            table_index=index,
            header_marked=any(cell.column_header for cell in grid[0]),
        )

    lines_by_page: dict[int | None, list[str]] = defaultdict(list)
    headers: list[tuple[int | None, str]] = []
    for item in document.texts:
        label = str(getattr(item.label, "value", item.label))
        text = (item.text or "").strip()
        if not text:
            continue
        if label == "page_header":
            headers.append((_page(item), text))
        elif label not in _SKIPPED_LABELS:
            lines_by_page[_page(item)].extend(text.splitlines())
    for page, lines in lines_by_page.items():
        facts += facts_from_lines(lines, page=page)
    if headers:
        page, text = headers[0]
        facts.append(FactDraft(page=page, label=_HEADER_LABEL, value=text[:300]))
    return dedupe(facts)[:MAX_FACTS]


def _page(item: Any) -> int | None:
    """Page of a Docling item.

    Args:
        item: Table or text item.

    Returns:
        Its 1-based page, or ``None`` when Docling does not know it.
    """
    provenance = getattr(item, "prov", None)
    return provenance[0].page_no if provenance else None
