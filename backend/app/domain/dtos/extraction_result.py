"""Outcome of classifying a document and extracting its fields."""

from dataclasses import dataclass

from app.domain.dtos.field_draft import FieldDraft
from app.domain.enums import DocumentType


@dataclass(frozen=True)
class ExtractionResult:
    """Outcome of processing one document.

    Attributes:
        document_type: Detected type, or ``None`` if classification failed.
        fields: Every field to store, including ``document_type`` itself.
    """

    document_type: DocumentType | None
    fields: list[FieldDraft]
