"""PDF extractor based on Docling (layout, tables and OCR).

Docling is the only text extractor of the application. It is installed only
in the worker image (extra ``docling``) and imported lazily, so the API and
the test image never need it.
"""

from functools import cache
from pathlib import Path
from typing import Any

from app.ai.ingestion.docling_facts import facts_from_docling
from app.ai.ingestion.pdf_pages import count_pages
from app.core.errors import CorruptPdfError, ExtractorUnavailableError, TooManyPagesError
from app.domain.dtos import ExtractedPdf, PageText


class DoclingExtractor:
    """Extract text with Docling (each page as Markdown) and its label-value data."""

    def extract(self, path: Path, *, max_pages: int) -> ExtractedPdf:
        """Extract the text of every page and the data of its tables and lines.

        The pages are counted first with pypdfium2: it is fast and avoids
        converting a document that will be rejected anyway.

        Args:
            path: PDF file on disk.
            max_pages: Maximum number of pages accepted.

        Returns:
            The text of every page, in order, and the data found.

        Raises:
            CorruptPdfError: If the file cannot be read or converted.
            TooManyPagesError: If the PDF has more than ``max_pages`` pages.
            ExtractorUnavailableError: If Docling is not installed.
        """
        page_count = count_pages(path)
        if page_count > max_pages:
            raise TooManyPagesError(f"The PDF has {page_count} pages; the limit is {max_pages}")

        try:
            document = _converter().convert(path).document
        except ExtractorUnavailableError:
            raise
        except Exception as exc:
            raise CorruptPdfError(f"Docling cannot convert the PDF: {exc}") from exc

        pages = [
            PageText(page=number, text=document.export_to_markdown(page_no=number))
            for number in range(1, page_count + 1)
        ]
        return ExtractedPdf(pages=pages, facts=facts_from_docling(document))


@cache
def _converter() -> Any:
    """Create the Docling converter once per process (it loads its models).

    Returns:
        The shared ``DocumentConverter``.

    Raises:
        ExtractorUnavailableError: If Docling is not installed.
    """
    try:
        from docling.document_converter import DocumentConverter
    except ImportError as exc:
        raise ExtractorUnavailableError(
            "Docling is not installed (install the 'docling' extra)"
        ) from exc
    return DocumentConverter()
