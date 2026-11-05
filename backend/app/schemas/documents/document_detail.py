"""A document with its extracted fields."""

from pydantic import Field

from app.schemas.documents.document_fact_out import DocumentFactOut
from app.schemas.documents.document_summary import DocumentSummary
from app.schemas.documents.extracted_field_out import ExtractedFieldOut


class DocumentDetail(DocumentSummary):
    """A document with its extracted fields.

    Attributes:
        chunk_count: Number of stored chunks.
        fields: Known fields (fixed list per document type).
        facts: Free label-value data of its tables and "campo: valor" lines.
    """

    chunk_count: int
    fields: list[ExtractedFieldOut]
    facts: list[DocumentFactOut] = Field(default_factory=list)
