"""A source supporting part of the answer."""

import uuid
from typing import Literal

from pydantic import BaseModel


class Citation(BaseModel):
    """A source supporting part of the answer.

    Attributes:
        marker: Number used in the answer text (``[1]`` -> ``1``).
        document_id: Cited document.
        filename: Original filename of the cited document.
        page: 1-based page number; ``None`` for an extracted field whose page
            is unknown.
        excerpt: Start of the cited fragment, or ``Label: value`` for a field.
        source: ``fragment`` (text of the document) or ``field`` (an
            extracted field, such as the invoice date).
        field: Field name when ``source`` is ``field`` (for example
            ``invoice_date``).
    """

    marker: int
    document_id: uuid.UUID
    filename: str
    page: int | None
    excerpt: str
    source: Literal["fragment", "field"] = "fragment"
    field: str | None = None
