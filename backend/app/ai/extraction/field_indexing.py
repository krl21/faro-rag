"""Turn extracted fields into the typed rows of the filter index."""

import logging
from collections.abc import Iterable, Sequence
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.text_normalization import normalize_identifier, normalize_name
from app.domain.dtos import FieldDraft, FieldValueDraft
from app.domain.enums import FieldStatus
from app.domain.indexed_fields import (
    AMOUNT_FIELD,
    DATE_FIELDS,
    IDENTIFIER_FIELDS,
    NAME_FIELDS,
    PERIOD_FIELDS,
)

logger = logging.getLogger(__name__)

_MAX_TEXT = 255
_INDEXED_STATUSES = frozenset({FieldStatus.OK, FieldStatus.EDITED})


def build_field_values(fields: Sequence[FieldDraft]) -> list[FieldValueDraft]:
    """Build the filter index rows of a document.

    Only fields with a value are indexed: ``ok`` and ``edited`` (corrected by
    the user). ``not_found`` and ``failed`` fields have no value to filter by.
    A value that cannot be indexed is skipped with a warning instead of
    failing the whole document.

    Args:
        fields: Fields extracted from the document.

    Returns:
        One row per atomic value (a list field yields one row per element).
    """
    rows: list[FieldValueDraft] = []
    for field in fields:
        if field.status not in _INDEXED_STATUSES or field.value is None:
            continue
        try:
            rows.extend(_index_field(field.name, field.value))
        except (TypeError, ValueError, KeyError, InvalidOperation) as exc:
            logger.warning(
                "field value not indexed", extra={"field": field.name, "error": str(exc)}
            )
    return rows


def _index_field(name: str, value: Any) -> Iterable[FieldValueDraft]:
    """Index one field value.

    Args:
        name: Field name.
        value: JSON value as stored in ``extracted_fields``.

    Returns:
        The rows for this field (none if it is not filterable).
    """
    values = value if isinstance(value, list) else [value]
    if name in IDENTIFIER_FIELDS:
        return [_text_row(name, normalize_identifier(str(v))) for v in values]
    if name in NAME_FIELDS:
        return [_text_row(name, normalize_name(str(v))) for v in values]
    if name in DATE_FIELDS:
        day = date.fromisoformat(value)
        return [FieldValueDraft(field_name=name, date_from=day, date_to=day)]
    if name in PERIOD_FIELDS:
        return [
            FieldValueDraft(
                field_name=name,
                date_from=date.fromisoformat(value["start"]),
                date_to=date.fromisoformat(value["end"]),
            )
        ]
    if name == AMOUNT_FIELD:
        return [
            FieldValueDraft(
                field_name=name,
                number_value=Decimal(str(value["amount"])),
                currency=value["currency"],
            )
        ]
    return []


def _text_row(name: str, text: str) -> FieldValueDraft:
    """Build a text row, truncated to the column size.

    Args:
        name: Field name.
        text: Normalized text.

    Returns:
        The row.
    """
    return FieldValueDraft(field_name=name, text_value=text[:_MAX_TEXT])
