"""A document with its extracted fields."""

from app.schemas.documents.document_summary import DocumentSummary
from app.schemas.documents.extracted_field_out import ExtractedFieldOut


class DocumentDetail(DocumentSummary):
    """A document with its extracted fields.

    Attributes:
        chunk_count: Number of stored chunks.
        fields: Extracted fields.
    """

    chunk_count: int
    fields: list[ExtractedFieldOut]
