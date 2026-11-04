"""Split page text into overlapping character-based chunks."""

import re
from collections.abc import Iterable

from app.domain.dtos import PageText, TextChunk

_WHITESPACE = re.compile(r"\s+")


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


def chunk_pages(pages: Iterable[PageText], size: int, overlap: int) -> list[TextChunk]:
    """Chunk every page independently.

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
        for index, content in enumerate(split_text(page.text, size, overlap))
    ]
