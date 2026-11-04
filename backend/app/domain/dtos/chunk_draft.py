"""A chunk ready to be stored."""

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkDraft:
    """A chunk ready to be stored.

    Attributes:
        page: 1-based page number.
        chunk_index: Position of the chunk inside its page.
        content: Chunk text.
        embedding: Embedding vector.
    """

    page: int
    chunk_index: int
    content: str
    embedding: Sequence[float]
