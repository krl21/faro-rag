"""A free label-value datum returned by a search, with its score."""

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class ScoredFact:
    """A free label-value datum returned by a search.

    Attributes:
        fact_id: Row identifier.
        document_id: Owning document.
        filename: Original file name of that document.
        page: 1-based page, when known.
        label: Label as written in the document.
        value: Value as written, or the columns of a table row.
        edited: Whether the user changed it.
        score: Cosine similarity (vector search) or ``ts_rank`` (text search).
    """

    fact_id: int
    document_id: uuid.UUID
    filename: str
    page: int | None
    label: str
    value: str | dict[str, str]
    edited: bool
    score: float
