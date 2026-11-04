"""Which date of a document a date expression in a question refers to."""

from enum import StrEnum


class DateTarget(StrEnum):
    """Which date of the document a match refers to."""

    UPLOADED = "uploaded"
    DOCUMENT = "document"
