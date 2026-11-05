"""Low-level PDF reading with pypdfium2: page count and embedded text layer.

pypdfium2 is small and has no PyTorch dependency, so the API, the worker and
the test image can all use it. Docling does the real text extraction (see
``docling_extractor``); this module only checks the file cheaply before the
conversion and reads attachments in the fake LLM provider.
"""

from pathlib import Path

import pypdfium2 as pdfium

from app.core.errors import CorruptPdfError


def count_pages(path: Path) -> int:
    """Count the pages of a PDF without converting it.

    Args:
        path: PDF file on disk.

    Returns:
        Number of pages.

    Raises:
        CorruptPdfError: If the file is missing, cannot be parsed or is encrypted.
    """
    try:
        document = pdfium.PdfDocument(path)
    except (pdfium.PdfiumError, ValueError, OSError) as exc:
        raise CorruptPdfError(f"The PDF cannot be read: {exc}") from exc
    try:
        return len(document)
    finally:
        document.close()


def read_text_layer(data: bytes) -> list[str]:
    """Read the embedded text of each page (no OCR, no layout).

    Args:
        data: PDF bytes.

    Returns:
        The text of every page, in order.

    Raises:
        CorruptPdfError: If the bytes are not a readable PDF.
    """
    try:
        document = pdfium.PdfDocument(data)
    except (pdfium.PdfiumError, ValueError) as exc:
        raise CorruptPdfError(f"The PDF cannot be read: {exc}") from exc
    try:
        return [_page_text(document[index]) for index in range(len(document))]
    finally:
        document.close()


def _page_text(page: pdfium.PdfPage) -> str:
    """Read the text of one page with Unix line breaks.

    Args:
        page: Open page.

    Returns:
        The page text.
    """
    text_page = page.get_textpage()
    try:
        return text_page.get_text_bounded().replace("\r\n", "\n")
    finally:
        text_page.close()
        page.close()
