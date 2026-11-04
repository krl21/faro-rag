"""Typed, normalized columns of an extracted field, used by the chat filters."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class FilterColumns:
    """Typed, normalized copy of a field value, stored next to its JSON value.

    Only the columns that apply to the field are set: a normalized text for
    identifiers and names, an amount with its currency, or a date range.

    Attributes:
        text_value: Normalized identifier (``FS2024001``) or name (``JUAN PEREZ``).
        number_value: Amount.
        currency: ISO 4217 code of the amount.
        date_from: First day of the date or period.
        date_to: Last day of the date or period.
    """

    text_value: str | None = None
    number_value: Decimal | None = None
    currency: str | None = None
    date_from: date | None = None
    date_to: date | None = None
