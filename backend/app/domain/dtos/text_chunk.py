"""A fragment of one page, before embedding."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    """A chunk of one page.

    Attributes:
        page: 1-based page number (chunks never cross pages, so each one has
            exactly one page to cite).
        chunk_index: Position of the chunk inside its page.
        content: Chunk text.
    """

    page: int
    chunk_index: int
    content: str
