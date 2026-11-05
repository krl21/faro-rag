"""PDF extractor for tests: reads the embedded text without Docling.

The test image does not install Docling (it pulls PyTorch and downloads
models). The PDFs built by ``pdf_factory`` have a plain text layer, so reading
it is enough to run the whole pipeline.
"""

from pathlib import Path

from app.ai.ingestion.fact_parsing import dedupe, facts_from_lines
from app.ai.ingestion.pdf_pages import count_pages, read_text_layer
from app.core.errors import TooManyPagesError
from app.domain.dtos import ExtractedPdf, PageText


class TextLayerExtractor:
    """Same contract as ``DoclingExtractor``, reading only the text layer.

    There are no tables in a text layer: the data come from its
    "campo: valor" lines, with the same rules as Docling's text.
    """

    def extract(self, path: Path, *, max_pages: int) -> ExtractedPdf:
        """Extract the text of every page and its "campo: valor" data.

        Args:
            path: PDF file on disk.
            max_pages: Maximum number of pages accepted.

        Returns:
            The text of every page and the data found.

        Raises:
            CorruptPdfError: If the file cannot be read.
            TooManyPagesError: If the PDF has more than ``max_pages`` pages.
        """
        page_count = count_pages(path)
        if page_count > max_pages:
            raise TooManyPagesError(f"The PDF has {page_count} pages; the limit is {max_pages}")
        texts = read_text_layer(path.read_bytes())
        pages = [PageText(page=number, text=text) for number, text in enumerate(texts, start=1)]
        facts = [f for p in pages for f in facts_from_lines(p.text.splitlines(), page=p.page)]
        return ExtractedPdf(pages=pages, facts=dedupe(facts))
