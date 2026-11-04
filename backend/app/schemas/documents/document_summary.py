"""A document as shown in lists."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.documents.document_error import DocumentError


class DocumentSummary(BaseModel):
    """A document as shown in lists.

    Attributes:
        id: Document identifier.
        filename: Original filename.
        status: ``pending``, ``processing``, ``done`` or ``failed``.
        document_type: ``policy``, ``invoice``, ``unknown`` (neither of them) or
            ``None`` if the classification failed.
        page_count: Number of pages, once extracted.
        size_bytes: File size.
        error: Processing error, if any.
        created_at: Upload time.
        updated_at: Last status change.
    """

    id: uuid.UUID
    filename: str
    status: str
    document_type: str | None
    page_count: int | None
    size_bytes: int
    error: DocumentError | None
    created_at: datetime
    updated_at: datetime
