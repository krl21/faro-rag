"""Result of reading a PDF: text per page and the label-value data found."""

from dataclasses import dataclass, field

from app.domain.dtos.fact_draft import FactDraft
from app.domain.dtos.page_text import PageText


@dataclass(frozen=True)
class ExtractedPdf:
    """Result of reading a PDF.

    Attributes:
        pages: Text of every page, in order.
        facts: Label-value data found in tables and "campo: valor" lines.
    """

    pages: list[PageText]
    facts: list[FactDraft] = field(default_factory=list)
