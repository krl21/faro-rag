"""Compute the typed, normalized filter columns of an extracted field."""

import dataclasses
import logging
from collections.abc import Sequence
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.flow_logging import fields as log_fields
from app.core.text_normalization import normalize_identifier, normalize_name
from app.domain.dtos import FieldDraft, FilterColumns
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


def filter_columns(field: FieldDraft) -> FilterColumns | None:
    """Compute the filter columns of one field.

    Only fields with a value are filterable: ``ok`` and ``edited`` (corrected
    by the user). ``not_found`` and ``failed`` fields, and fields the chat
    cannot filter by (coverages, document type), get ``None``. A value that
    cannot be converted is skipped with a warning instead of failing the
    whole document.

    Args:
        field: Extracted (or edited) field.

    Returns:
        The columns to store next to the JSON value, or ``None``.
    """
    if field.status not in _INDEXED_STATUSES or field.value is None:
        return None
    try:
        return _columns(field.name, field.value)
    except (TypeError, ValueError, KeyError, InvalidOperation) as exc:
        logger.warning(
            "field value not indexed", extra=log_fields(field=field.name, error=str(exc))
        )
        return None


def with_filter_columns(fields: Sequence[FieldDraft]) -> list[FieldDraft]:
    """Attach the filter columns to every field.

    Args:
        fields: Fields extracted from a document.

    Returns:
        The same fields with ``filter_columns`` set where it applies.
    """
    return [dataclasses.replace(f, filter_columns=filter_columns(f)) for f in fields]


def _columns(name: str, value: Any) -> FilterColumns | None:
    """Convert a field value into its filter columns.

    Args:
        name: Field name.
        value: JSON value as stored in ``extracted_fields.value``.

    Returns:
        The columns, or ``None`` if the field is not filterable.

    Raises:
        ValueError: If a filterable value is a list (one row per field holds
            a single value) or cannot be converted.
    """
    is_filterable = name in IDENTIFIER_FIELDS | NAME_FIELDS | DATE_FIELDS | PERIOD_FIELDS | {
        AMOUNT_FIELD
    }
    if is_filterable and isinstance(value, list):
        raise ValueError("filterable fields hold a single value, not a list")
    if name in IDENTIFIER_FIELDS:
        return FilterColumns(text_value=normalize_identifier(str(value))[:_MAX_TEXT])
    if name in NAME_FIELDS:
        return FilterColumns(text_value=normalize_name(str(value))[:_MAX_TEXT])
    if name in DATE_FIELDS:
        day = date.fromisoformat(value)
        return FilterColumns(date_from=day, date_to=day)
    if name in PERIOD_FIELDS:
        return FilterColumns(
            date_from=date.fromisoformat(value["start"]),
            date_to=date.fromisoformat(value["end"]),
        )
    if name == AMOUNT_FIELD:
        return FilterColumns(number_value=Decimal(str(value["amount"])), currency=value["currency"])
    return None
