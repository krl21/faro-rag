"""An extracted field of a document, given to the LLM as a citable source."""

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class FieldFact:
    """An extracted field of a document, given to the LLM as a citable source.

    Attributes:
        document_id: Document the field belongs to.
        filename: Original file name of that document.
        page: 1-based page where the value was found, when known.
        name: Field name (for example ``invoice_date``).
        label: Spanish label shown to the LLM (for example ``Fecha de la factura``).
        value: Value as readable text (``2026-04-22``, ``1250.50 EUR``...).
        edited: Whether the user corrected the value.
    """

    document_id: uuid.UUID
    filename: str
    page: int | None
    name: str
    label: str
    value: str
    edited: bool = False
