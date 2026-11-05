"""Find label-value data in tables and in text lines.

Insurance documents give most of their data as labels next to values, in
several layouts:

- **Vertical table**: one label per row, its value in the next column
  (``Fecha de emisión | 22/04/2026``).
- **Horizontal table**: labels in the header row, values in the row below
  (``Póliza | Fecha | Importe`` over ``FS-1 | 01/01/2026 | 100,00 €``).
- **Table of records**: a header row and several data rows (invoice lines,
  coverages). Each row becomes one datum with every column of the row.
- **Lines without a table**: ``Titular: ACME`` one under another (also
  several pairs on the same line), a label line followed by its value line
  (``TOTAL FACTURA`` / ``40.492,65 €``), ``Base imponible 33.465,00 €`` or
  ``FACTURA N.º ABS-1``.

Only data written in the document are returned: nothing is inferred.
"""

import re
from collections.abc import Sequence

from app.domain.dtos import FactDraft

MAX_LABEL_CHARS = 60
MAX_VALUE_CHARS = 300
# Outside tables, a longer value after "Label:" is prose ("Nuestra misión es: ...").
_MAX_LINE_VALUE_CHARS = 150
_MAX_LABEL_WORDS = 6
_MAX_VALUE_LIKE_CHARS = 60
_MAX_VALUE_LIKE_WORDS = 6

_HAS_DIGIT = re.compile(r"\d")
_HAS_LETTER = re.compile(r"[^\W\d_]")
# A value starts with a digit, a sign or a currency symbol, or is a single code.
_VALUE_START = re.compile(r"^[\d+\-−(€$]")
# Start of a "Label:" inside a line that holds several pairs.
_PAIR_START = re.compile(r"(?<=\S)\s+(?=[A-ZÁÉÍÓÚÑ][\w.º/() -]{0,40}?:\s)")
_COLON_PAIR = re.compile(r"^(?P<label>[^:]{2,60}?)\s*:\s*(?P<value>.*)$")
_NUMBER_SIGN = re.compile(
    r"^(?P<label>.{2,50}?\b(?:N\.?\s?º|Nº|núm\.?|número))\s*(?P<value>[A-Z0-9][A-Z0-9\-/.]{2,})$",
    re.IGNORECASE,
)
_AMOUNT = r"-?\d{1,3}(?:\.\d{3})*,\d{2}\s?(?:€|EUR)?|-?\d+[.,]\d{2}\s?(?:€|EUR)"
_DATE = r"\d{1,2}/\d{1,2}/\d{2,4}"
_TRAILING_VALUE = re.compile(rf"^(?P<label>\D.{{1,48}}?)\s+(?P<value>{_AMOUNT}|{_DATE})$")


def describe(label: str, value: str | dict[str, str]) -> str:
    """Render a datum as one line of text (for the LLM and the search index).

    Args:
        label: Label of the datum.
        value: Its value, or the columns of a table row.

    Returns:
        ``Label: value``, or ``Column: value; Column: value`` for a table row.
    """
    if isinstance(value, dict):
        return "; ".join(f"{column}: {cell}" for column, cell in value.items())
    return f"{label}: {value}"


def facts_from_grid(
    grid: Sequence[Sequence[str]],
    *,
    page: int | None,
    table_index: int,
    header_marked: bool = False,
) -> list[FactDraft]:
    """Turn a table into data, detecting whether it is vertical, horizontal or records.

    Args:
        grid: Text of every cell, row by row.
        page: Page of the table.
        table_index: Position of the table in the document.
        header_marked: Whether the extractor marked the first row as a header.

    Returns:
        The data of the table (empty cells are skipped).
    """
    rows = _clean_grid(grid)
    if not rows or len(rows[0]) < 2:
        return []
    columns = len(rows[0])
    first, rest = rows[0], rows[1:]
    has_header = header_marked or _looks_like_header(first, rest)

    def pair(row: int | None, label: str, value: str) -> FactDraft | None:
        return _fact(page, label, value, table_index=table_index, row_index=row)

    facts: list[FactDraft | None] = []
    if columns == 2:
        # Vertical: each row is "label | value" (a marked header row is skipped).
        body = rest if header_marked else rows
        facts = [pair(i, label, value) for i, (label, value) in enumerate(body)]
    elif len(rows) == 2 and has_header:
        # Horizontal: labels in the first row, values in the second.
        facts = [pair(0, label, value) for label, value in zip(first, rest[0], strict=True)]
    else:
        # Records: one datum per data row, with all its columns.
        header = first if has_header else [f"Columna {c + 1}" for c in range(columns)]
        body = rest if has_header else rows
        for i, row in enumerate(body):
            cells = {
                (h or f"Columna {c + 1}"): v
                for c, (h, v) in enumerate(zip(header, row, strict=True))
                if v
            }
            label = next((v for v in row if v), "")
            if len(cells) >= 2 and label:
                facts.append(
                    FactDraft(
                        page=page,
                        label=label[:MAX_LABEL_CHARS],
                        value={k[:MAX_LABEL_CHARS]: v[:MAX_VALUE_CHARS] for k, v in cells.items()},
                        table_index=table_index,
                        row_index=i,
                    )
                )
    return [f for f in facts if f is not None]


def facts_from_lines(lines: Sequence[str], *, page: int | None) -> list[FactDraft]:
    """Find "campo: valor" data in lines of text that are not in a table.

    Args:
        lines: Lines (or short text blocks) of one page, in reading order.
        page: Page of the lines.

    Returns:
        The data found, in reading order.
    """
    cleaned = [" ".join(line.split()) for line in lines]
    cleaned = [line for line in cleaned if line]
    facts: list[FactDraft] = []
    i = 0
    while i < len(cleaned):
        line = cleaned[i]
        following = cleaned[i + 1] if i + 1 < len(cleaned) else None
        found, used_next = _facts_in_line(line, following, page)
        facts.extend(found)
        i += 2 if used_next else 1
    return facts


def dedupe(facts: Sequence[FactDraft]) -> list[FactDraft]:
    """Drop repeated data (same page, label and value), keeping the first one.

    Args:
        facts: Data in document order.

    Returns:
        The data without repetitions.
    """
    seen: set[tuple] = set()
    unique = []
    for fact in facts:
        key = (fact.page, fact.label, describe(fact.label, fact.value))
        if key not in seen:
            seen.add(key)
            unique.append(fact)
    return unique


def _facts_in_line(
    line: str, following: str | None, page: int | None
) -> tuple[list[FactDraft], bool]:
    """Find the data of one line, possibly using the next one as its value.

    Args:
        line: Current line.
        following: Next line, or ``None``.
        page: Page of the line.

    Returns:
        The data found and whether the next line was used as a value.
    """
    if match := _COLON_PAIR.match(line):
        label, value = match["label"], match["value"]
        if _is_label(label) and len(value) <= _MAX_LINE_VALUE_CHARS:
            if not value and following is not None and _is_value_like(following):
                fact = _fact(page, label, following)
                return ([fact] if fact else []), True
            facts = []
            for segment in _PAIR_START.split(f"{label}: {value}"):
                if (part := _COLON_PAIR.match(segment)) and _is_label(part["label"]):
                    fact = _fact(page, part["label"], part["value"])
                    if fact:
                        facts.append(fact)
            if facts:
                return facts, False
    for pattern in (_NUMBER_SIGN, _TRAILING_VALUE):
        if (match := pattern.match(line)) and _is_label(match["label"]):
            fact = _fact(page, match["label"], match["value"])
            if fact:
                return [fact], False
    # A label line followed by its value line ("TOTAL FACTURA" / "40.492,65 €").
    if (
        following is not None
        and _is_label(line)
        and not _is_value_like(line)
        and _is_value_like(following)
    ):
        fact = _fact(page, line, following)
        return ([fact] if fact else []), True
    return [], False


def _fact(
    page: int | None,
    label: str,
    value: str,
    *,
    table_index: int | None = None,
    row_index: int | None = None,
) -> FactDraft | None:
    """Build a datum, or ``None`` when the label or the value is empty.

    Args:
        page: Page of the datum.
        label: Label text.
        value: Value text.
        table_index: Table of the datum, if any.
        row_index: Row of the datum, if any.

    Returns:
        The datum, with label and value trimmed to their maximum length.
    """
    label = label.strip(" :·-")
    value = value.strip()
    if not label or not value or not _HAS_LETTER.search(label):
        return None
    return FactDraft(
        page=page,
        label=label[:MAX_LABEL_CHARS],
        value=value[:MAX_VALUE_CHARS],
        table_index=table_index,
        row_index=row_index,
    )


def _is_label(text: str) -> bool:
    """Tell whether a text can be a label: short, with letters, not a sentence.

    Args:
        text: Candidate label.

    Returns:
        ``True`` for texts such as ``Fecha de emisión`` or ``IVA 21 %``.
    """
    text = text.strip()
    return (
        0 < len(text) <= MAX_LABEL_CHARS
        and len(text.split()) <= _MAX_LABEL_WORDS
        and bool(_HAS_LETTER.search(text))
        and not text.endswith((".", ",", ";"))
    )


def _is_value_like(text: str) -> bool:
    """Tell whether a short text looks like a value (amount, date, code...).

    Args:
        text: Candidate value.

    Returns:
        ``True`` for short texts with a digit that start like a value
        (``40.492,65 €``, ``4417 MRT``) or are a single code (``B-11000005``);
        ``False`` for labels with digits such as ``IVA 21 %``.
    """
    return (
        len(text) <= _MAX_VALUE_LIKE_CHARS
        and len(text.split()) <= _MAX_VALUE_LIKE_WORDS
        and bool(_HAS_DIGIT.search(text))
        and ":" not in text
        and (bool(_VALUE_START.match(text)) or len(text.split()) == 1)
    )


def _looks_like_header(first: Sequence[str], rest: Sequence[Sequence[str]]) -> bool:
    """Guess whether the first row of an unmarked table is a header.

    Args:
        first: First row.
        rest: The other rows.

    Returns:
        ``True`` when every cell of the first row is a label without digits
        and the other rows hold values with digits.
    """
    if not rest or not all(cell and not _HAS_DIGIT.search(cell) for cell in first):
        return False
    return any(_HAS_DIGIT.search(cell) for row in rest for cell in row)


def _clean_grid(grid: Sequence[Sequence[str]]) -> list[list[str]]:
    """Normalize whitespace and drop empty rows and columns.

    Args:
        grid: Raw cell texts.

    Returns:
        A rectangular grid without empty rows or columns.
    """
    rows = [[" ".join((cell or "").split()) for cell in row] for row in grid]
    rows = [row for row in rows if any(row)]
    if not rows:
        return []
    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]
    keep = [c for c in range(width) if any(row[c] for row in rows)]
    return [[row[c] for c in keep] for row in rows]
