"""Summary of a document processing run."""

from dataclasses import dataclass

from app.domain.enums import DocumentStatus


@dataclass(frozen=True)
class ProcessingOutcome:
    """Summary of a processing run.

    Attributes:
        status: Final document status.
        chunk_count: Chunks stored.
        failed_fields: Number of fields stored with ``status=failed``.
    """

    status: DocumentStatus
    chunk_count: int = 0
    failed_fields: int = 0
