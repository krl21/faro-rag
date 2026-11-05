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
        name: Field name (for example ``invoice_date``), or ``None`` for a
            free label-value datum found in a table or line of the document.
        label: Label shown to the LLM: the Spanish label of a known field
            (``Fecha de emisión de la factura``) or the label as written.
        value: Value as readable text (``2026-04-22``, ``1250.50 EUR``...).
        edited: Whether the user corrected the value.
    """

    document_id: uuid.UUID
    filename: str
    page: int | None
    name: str | None
    label: str
    value: str
    edited: bool = False
