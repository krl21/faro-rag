"""A chunk selected as evidence for an answer."""

from dataclasses import dataclass

from app.domain.dtos.scored_chunk import ScoredChunk


@dataclass(frozen=True)
class RetrievedChunk:
    """A chunk selected as evidence for an answer.

    Attributes:
        chunk: The chunk and its metadata.
        similarity: Cosine similarity to the question (``None`` if it was
            found only by full-text search).
        keyword_match: Whether full-text search matched the chunk.
        fused_score: Reciprocal Rank Fusion score used for ordering.
    """

    chunk: ScoredChunk
    similarity: float | None
    keyword_match: bool
    fused_score: float
