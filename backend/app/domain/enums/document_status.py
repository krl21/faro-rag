"""Processing lifecycle of a document."""

from enum import StrEnum


class DocumentStatus(StrEnum):
    """Processing lifecycle of a document."""

    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"
