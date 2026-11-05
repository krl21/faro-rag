"""PDF text extraction interface and the check for pages with text."""

from pathlib import Path
from typing import Protocol

from app.core.errors import NoExtractableTextError
from app.domain.dtos import ExtractedPdf, PageText

# Pages with fewer meaningful characters are treated as empty (scans, blank pages).
MIN_PAGE_CHARS = 20


class PdfExtractor(Protocol):
    """Extracts the text of a PDF, page by page, and its label-value data."""

    def extract(self, path: Path, *, max_pages: int) -> ExtractedPdf:
        """Extract the text of every page and the data of its tables and lines.

        Args:
            path: PDF file on disk.
            max_pages: Maximum number of pages accepted.

        Returns:
            The text of every page, in order, and the data found.

        Raises:
            CorruptPdfError: If the file cannot be parsed.
            TooManyPagesError: If the PDF has more than ``max_pages`` pages.
        """
        ...


def ensure_has_text(pages: list[PageText]) -> list[PageText]:
    """Keep the pages with meaningful text and fail if none remain.

    Args:
        pages: Pages returned by an extractor.

    Returns:
        Pages with at least ``MIN_PAGE_CHARS`` non-whitespace characters.

    Raises:
        NoExtractableTextError: If no page has meaningful text (for example a
            scanned PDF without an OCR layer).
    """
    useful = [p for p in pages if len("".join(p.text.split())) >= MIN_PAGE_CHARS]
    if not useful:
        raise NoExtractableTextError(
            "The PDF has no extractable text (it may be a scanned document)"
        )
    return useful
