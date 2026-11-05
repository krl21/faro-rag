"""What the LLM receives as the document in classification and extraction."""

from enum import StrEnum


class DocumentInput(StrEnum):
    """What the LLM receives as the document in classification and extraction.

    ``PDF`` attaches the original file (needs a model with PDF input).
    ``TEXT`` sends the text extracted by Docling, with page markers, for
    models that only accept text.
    """

    PDF = "pdf"
    TEXT = "text"
