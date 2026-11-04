"""Text of one PDF page."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PageText:
    """Text of one PDF page.

    Attributes:
        page: 1-based page number.
        text: Extracted text.
    """

    page: int
    text: str
