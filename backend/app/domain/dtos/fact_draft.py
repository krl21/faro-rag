"""A label-value datum found in a document (table cell, table row or "campo: valor")."""

from dataclasses import dataclass


@dataclass(frozen=True)
class FactDraft:
    """A label-value datum found in a document, before it is stored.

    Attributes:
        page: 1-based page where it appears, when known.
        label: Label as written in the document (``Fecha de emisión``). For a
            row of a table with several columns, the text of its first cell.
        value: The value as written (``22/04/2026``), or, for a row of a table
            with several columns, every column of the row (``{"Concepto":
            "Kit", "Importe": "1.280,00 €"}``).
        table_index: Position of its table in the document (0-based), or
            ``None`` when it is not in a table.
        row_index: Row of the table (0-based, header excluded), or ``None``.
    """

    page: int | None
    label: str
    value: str | dict[str, str]
    table_index: int | None = None
    row_index: int | None = None
