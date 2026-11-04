"""An indexed value ready to be stored. Only the relevant columns are set."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class FieldValueDraft:
    """An indexed value ready to be stored. Only the relevant columns are set.

    Attributes:
        field_name: Extracted field name (for example ``policy_number``).
        text_value: Normalized identifier or name.
        number_value: Amount.
        currency: ISO 4217 code of the amount.
        date_from: First day of the date or period.
        date_to: Last day of the date or period.
    """

    field_name: str
    text_value: str | None = None
    number_value: Decimal | None = None
    currency: str | None = None
    date_from: date | None = None
    date_to: date | None = None
