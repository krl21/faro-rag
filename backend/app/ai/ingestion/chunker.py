"""Split page text into chunks: prose by characters, tables by whole rows.

Docling exports each page as Markdown, with tables as ``| a | b |`` lines. A
character-based cut would leave half a row in one chunk and half in the next,
so tables are chunked apart: whole rows only, and every chunk of a table
repeats its header (and the section heading above it), so each one can be
understood alone. The rest of the page is split by characters with overlap.
"""

import re
from collections.abc import Iterable, Sequence

from app.domain.dtos import PageText, TextChunk

_WHITESPACE = re.compile(r"\s+")
_SPACES = re.compile(r"[ \t]+")
_TABLE_LINE = re.compile(r"^\s*\|.*\|\s*$")
_SEPARATOR = re.compile(r"^\s*\|[\s:\-|]+\|\s*$")
_HEADING = re.compile(r"^\s*#{1,6}\s+\S")


def split_text(text: str, size: int, overlap: int) -> list[str]:
    """Split text into chunks of at most ``size`` characters.

    Consecutive chunks share about ``overlap`` characters. Cuts are moved
    back to the last whitespace inside the window so words are not broken.

    Args:
        text: Text to split. Whitespace is collapsed first.
        size: Maximum chunk length in characters.
        overlap: Characters shared by consecutive chunks; must be < ``size``.

    Returns:
        The chunks, in order. Empty text yields an empty list.

    Raises:
        ValueError: If ``size`` is not positive or ``overlap`` is out of range.
    """
    if size <= 0:
        raise ValueError("size must be positive")
    if not 0 <= overlap < size:
        raise ValueError("overlap must be >= 0 and smaller than size")

    clean = _WHITESPACE.sub(" ", text).strip()
    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(start + size, len(clean))
        if end < len(clean):
            cut = clean.rfind(" ", start + overlap + 1, end)
            if cut != -1:
                end = cut
        chunk = clean[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(clean):
            break
        next_start = end - overlap
        # Start the overlap on a word boundary when possible.
        boundary = clean.find(" ", next_start, end)
        start = boundary + 1 if boundary != -1 else next_start
    return chunks


def split_page(text: str, size: int, overlap: int) -> list[str]:
    """Split a page: prose by characters, each table by whole rows.

    Args:
        text: Page text (Markdown from Docling, or plain text).
        size: Maximum chunk length in characters.
        overlap: Characters shared by consecutive prose chunks.

    Returns:
        The chunks of the page, in reading order.
    """
    lines = text.splitlines()
    chunks: list[str] = []
    prose: list[str] = []
    heading: str | None = None
    i = 0
    while i < len(lines):
        end = i
        while end < len(lines) and _TABLE_LINE.match(lines[end]):
            end += 1
        if end - i >= 2:  # A table: at least a header and one row.
            # The heading right above the table goes with the table, not alone.
            while prose and (not prose[-1].strip() or prose[-1].strip() == heading):
                prose.pop()
            chunks += split_text("\n".join(prose), size, overlap)
            prose = []
            chunks += split_table(lines[i:end], size, heading)
            i = end
            continue
        if _HEADING.match(lines[i]):
            heading = lines[i].strip()
        prose.append(lines[i])
        i += 1
    chunks += split_text("\n".join(prose), size, overlap)
    return chunks


def split_table(lines: Sequence[str], size: int, heading: str | None = None) -> list[str]:
    """Split a Markdown table into chunks of whole rows, repeating its header.

    Args:
        lines: Table lines (``| a | b |``), header first.
        size: Maximum chunk length in characters. A single row longer than
            that is kept whole in its own chunk (a row is never cut).
        heading: Section heading above the table, repeated in every chunk.

    Returns:
        The chunks of the table.
    """
    rows = [_SPACES.sub(" ", line.strip()) for line in lines]
    if len(rows) >= 2 and _SEPARATOR.match(rows[1]):
        cells = rows[0].count("|") - 1
        prefix, body = [rows[0], "|" + "---|" * cells], rows[2:]
    else:
        prefix, body = [], rows
    if heading:
        prefix = [heading, *prefix]
    if not body:
        return ["\n".join(prefix)]

    chunks: list[str] = []
    current = list(prefix)
    for row in body:
        if len(current) > len(prefix) and len("\n".join([*current, row])) > size:
            chunks.append("\n".join(current))
            current = list(prefix)
        current.append(row)
    chunks.append("\n".join(current))
    return chunks


def chunk_pages(pages: Iterable[PageText], size: int, overlap: int) -> list[TextChunk]:
    """Chunk every page independently (tables by whole rows, see ``split_page``).

    Args:
        pages: Extracted pages.
        size: Maximum chunk length in characters.
        overlap: Characters shared by consecutive chunks.

    Returns:
        All chunks with their page number and position.
    """
    return [
        TextChunk(page=page.page, chunk_index=index, content=content)
        for page in pages
        for index, content in enumerate(split_page(page.text, size, overlap))
    ]
