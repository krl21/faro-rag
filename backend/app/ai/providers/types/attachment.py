"""A file sent to the model together with a message."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Attachment:
    """A file sent to the model together with a message (for example, a PDF).

    Attributes:
        data: Raw file bytes.
        mime_type: Media type, for example ``application/pdf``.
        filename: Original file name, informative only.
    """

    data: bytes
    mime_type: str
    filename: str = "document"
