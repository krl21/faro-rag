"""A source supporting part of the answer."""

import uuid

from pydantic import BaseModel


class Citation(BaseModel):
    """A source supporting part of the answer.

    Attributes:
        marker: Number used in the answer text (``[1]`` -> ``1``).
        document_id: Cited document.
        filename: Original filename of the cited document.
        page: 1-based page number.
        excerpt: Start of the cited fragment.
    """

    marker: int
    document_id: uuid.UUID
    filename: str
    page: int
    excerpt: str
