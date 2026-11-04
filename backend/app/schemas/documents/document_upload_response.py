"""Result of ``POST /documents``."""

import uuid

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    """Result of ``POST /documents``.

    Attributes:
        id: Identifier of the new (or already existing) document.
        status: Current status.
        duplicate: ``True`` when a file with the same content already existed.
        message: Notification for the client, set for duplicates.
    """

    id: uuid.UUID
    status: str
    duplicate: bool
    message: str | None = None
