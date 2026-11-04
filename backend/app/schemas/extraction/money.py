"""A monetary amount."""

from decimal import Decimal
from typing import Annotated

from pydantic import BeforeValidator, Field

from app.schemas.extraction.spanish_input import SpanishInput
from app.schemas.helpers import upper_currency


class Money(SpanishInput):
    """A monetary amount.

    Attributes:
        amount: Non-negative amount (``importe``).
        currency: ISO 4217 code (``moneda``), for example ``EUR``; upper-cased.
    """

    amount: Decimal = Field(alias="importe", ge=0, max_digits=14, decimal_places=2)
    currency: Annotated[str, BeforeValidator(upper_currency)] = Field(
        alias="moneda", pattern=r"^[A-Z]{3}$"
    )
