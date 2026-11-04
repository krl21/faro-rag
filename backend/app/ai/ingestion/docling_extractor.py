"""Optional PDF extractor based on Docling (tables, layout and OCR).

Docling is an optional dependency (extra ``docling``) installed only in the
worker image. It is imported lazily so the API never needs it.
"""

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.errors import CorruptPdfError, ExtractorUnavailableError, TooManyPagesError
from app.domain.dtos import PageText


class DoclingExtractor:
    """Extract text with Docling, exporting each page as Markdown."""

    def extract(self, path: Path, *, max_pages: int) -> list[PageText]:
        """Extract the text of every page.

        Args:
            path: PDF file on disk.
            max_pages: Maximum number of pages accepted.

        Returns:
            One entry per page, in order.

        Raises:
            ExtractorUnavailableError: If Docling is not installed.
            CorruptPdfError: If Docling cannot convert the file.
            TooManyPagesError: If the PDF has more than ``max_pages`` pages.
        """
        try:
            from docling.document_converter import DocumentConverter
        except ImportError as exc:
            raise ExtractorUnavailableError(
                "Docling is not installed (install the 'docling' extra)"
            ) from exc

        # Count pages with pypdf first: it is fast and avoids converting a
        # document that will be rejected anyway.
        try:
            page_count = len(PdfReader(path).pages)
        except (PdfReadError, ValueError, OSError) as exc:
            raise CorruptPdfError(f"The PDF cannot be read: {exc}") from exc
        if page_count > max_pages:
            raise TooManyPagesError(f"The PDF has {page_count} pages; the limit is {max_pages}")

        try:
            document = DocumentConverter().convert(path).document
        except Exception as exc:
            raise CorruptPdfError(f"Docling cannot convert the PDF: {exc}") from exc

        return [
            PageText(page=number, text=document.export_to_markdown(page_no=number))
            for number in range(1, page_count + 1)
        ]
