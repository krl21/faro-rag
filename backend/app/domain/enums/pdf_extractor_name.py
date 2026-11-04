"""Available PDF text extractors (``PDF_EXTRACTOR``)."""

from enum import StrEnum


class PdfExtractorName(StrEnum):
    """Available PDF text extractors (``PDF_EXTRACTOR``)."""

    PYPDF = "pypdf"
    DOCLING = "docling"
