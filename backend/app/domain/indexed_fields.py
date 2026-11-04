"""Which extracted fields are indexed for chat filters, and how they compare.

Shared by the indexer (when a document is processed) and by the filter
queries (when a question is asked), so both sides always agree.
"""

from app.domain.enums import FilterField

IDENTIFIER_FIELDS: frozenset[str] = frozenset({"policy_number", "tax_id", "license_plate"})
"""Compared exactly after ``normalize_identifier`` (``FW-23`` == ``fw 23``)."""

NAME_FIELDS: frozenset[str] = frozenset({"holder", "issuer"})
"""Compared partially after ``normalize_name`` (``Pérez`` finds ``Juan Pérez``)."""

AMOUNT_FIELD = "invoice_amount"
"""Field used by the amount range filter."""

DATE_FIELDS: frozenset[str] = frozenset({"document_date", "invoice_date"})
"""Single dates used by the document date filter."""

PERIOD_FIELDS: frozenset[str] = frozenset({"validity"})
"""Periods used by the document date filter (a policy matches if its validity overlaps)."""

DOCUMENT_DATE_FIELDS: frozenset[str] = DATE_FIELDS | PERIOD_FIELDS
"""Every field the ``fecha_documento`` filter looks at."""


def is_identifier(field: FilterField) -> bool:
    """Tell whether a filter field is compared exactly.

    Args:
        field: Filter field.

    Returns:
        ``True`` for identifiers, ``False`` for names.
    """
    return field.value in IDENTIFIER_FIELDS
