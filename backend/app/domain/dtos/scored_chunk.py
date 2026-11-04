"""A chunk returned by a search, with its document metadata and score."""

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class ScoredChunk:
    """A chunk returned by a search, with its document metadata and score.

    Attributes:
        chunk_id: Chunk identifier.
        document_id: Owning document.
        filename: Original filename of the document.
        page: 1-based page number.
        content: Chunk text.
        score: Cosine similarity (vector search) or ``ts_rank`` (full-text search).
    """

    chunk_id: int
    document_id: uuid.UUID
    filename: str
    page: int
    content: str
    score: float
