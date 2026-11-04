"""PDF text extraction interface and extractor selection."""

from pathlib import Path
from typing import Protocol

from app.config import Settings
from app.core.errors import NoExtractableTextError
from app.domain.dtos import PageText
from app.domain.enums import PdfExtractorName

# Pages with fewer meaningful characters are treated as empty (scans, blank pages).
MIN_PAGE_CHARS = 20


class PdfExtractor(Protocol):
    """Extracts text from a PDF, page by page."""

    def extract(self, path: Path, *, max_pages: int) -> list[PageText]:
        """Extract the text of every page.

        Args:
            path: PDF file on disk.
            max_pages: Maximum number of pages accepted.

        Returns:
            One entry per page, in order.

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


def build_pdf_extractor(settings: Settings) -> PdfExtractor:
    """Create the extractor selected by ``PDF_EXTRACTOR``.

    Args:
        settings: Application settings.

    Returns:
        The configured extractor.
    """
    if settings.pdf_extractor is PdfExtractorName.DOCLING:
        from app.ai.ingestion.docling_extractor import DoclingExtractor

        return DoclingExtractor()
    from app.ai.ingestion.pypdf_extractor import PypdfExtractor

    return PypdfExtractor()
