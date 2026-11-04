"""Default PDF extractor based on pypdf (light and fast)."""

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.errors import CorruptPdfError, TooManyPagesError
from app.domain.dtos import PageText


class PypdfExtractor:
    """Extract embedded text with pypdf. It does not perform OCR."""

    def extract(self, path: Path, *, max_pages: int) -> list[PageText]:
        """Extract the text of every page.

        Args:
            path: PDF file on disk.
            max_pages: Maximum number of pages accepted.

        Returns:
            One entry per page, in order.

        Raises:
            CorruptPdfError: If pypdf cannot parse the file or it is encrypted.
            TooManyPagesError: If the PDF has more than ``max_pages`` pages.
        """
        try:
            reader = PdfReader(path)
            if reader.is_encrypted:
                raise CorruptPdfError("The PDF is encrypted")
            page_count = len(reader.pages)
        except CorruptPdfError:
            raise
        except (PdfReadError, ValueError, OSError) as exc:
            raise CorruptPdfError(f"The PDF cannot be read: {exc}") from exc

        if page_count > max_pages:
            raise TooManyPagesError(f"The PDF has {page_count} pages; the limit is {max_pages}")

        pages: list[PageText] = []
        for number, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception as exc:
                raise CorruptPdfError(f"Page {number} cannot be read: {exc}") from exc
            pages.append(PageText(page=number, text=text))
        return pages
