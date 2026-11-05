"""A document as it can be sent to the LLM: original PDF and extracted text."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LLMDocument:
    """A document as it can be sent to the LLM.

    Both forms are kept so the configured ``DocumentInput`` decides which one
    each prompt uses.

    Attributes:
        pdf: Original PDF bytes.
        filename: Original file name, sent with the PDF.
        text: Extracted text of every page, each one preceded by a
            ``[Página n]`` marker.
        page_count: Pages of the PDF; a page reported by the LLM beyond it
            is discarded.
        facts: Label-value data found in its tables and lines, one per line
            with its page (``[Página 1] TOTAL FACTURA: 40.492,65 €``). Given to
            the field extraction as a hint, so no value is overlooked.
    """

    pdf: bytes
    filename: str
    text: str
    page_count: int
    facts: str = ""
