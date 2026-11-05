"""A document type mentioned in a question."""

from dataclasses import dataclass

from app.domain.enums import DocumentType


@dataclass(frozen=True)
class TypeMatch:
    """A document type mentioned in the question.

    Attributes:
        start: First character.
        end: One past the last character.
        document_type: Mentioned type.
    """

    start: int
    end: int
    document_type: DocumentType
