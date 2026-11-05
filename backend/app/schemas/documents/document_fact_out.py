"""A free label-value datum of a document (table or "campo: valor" line)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DocumentFactOut(BaseModel):
    """A free label-value datum found in a table or line of the document.

    Attributes:
        id: Identifier, used to edit or delete it.
        label: Label as written in the document (``TOTAL FACTURA``); for a
            row of a table with several columns, the text of its first cell.
        value: The value as written, or, for such a row, an object with every
            column of the row (``{"Concepto": "Kit", "Importe": "1.280,00 €"}``).
        page: 1-based page where it appears, when known.
        table_index: Position of its table in the document (0-based), or
            ``None`` when it is not in a table.
        row_index: Row of the table (0-based), or ``None``.
        status: ``ok`` (as found) or ``edited`` (changed by the user).
        original_value: ``{"label": ..., "value": ...}`` as found, before
            the first edit.
        edited_at: When the user last edited it.
    """

    id: int
    label: str
    value: str | dict[str, str]
    page: int | None
    table_index: int | None = None
    row_index: int | None = None
    status: str
    original_value: dict[str, Any] | None = None
    edited_at: datetime | None = None
