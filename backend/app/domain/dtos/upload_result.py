"""Outcome of a document upload."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models import Document


@dataclass(frozen=True)
class UploadResult:
    """Outcome of an upload.

    Attributes:
        document: The new or existing document.
        duplicate: ``True`` when the content was already uploaded.
        requeued: ``True`` when the existing document had failed and its
            processing was enqueued again.
    """

    document: Document
    duplicate: bool
    requeued: bool = False
