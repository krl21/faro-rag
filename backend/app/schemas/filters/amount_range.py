"""Inclusive amount range; either end may be open."""

from decimal import Decimal
from typing import Annotated

from pydantic import BeforeValidator, Field, model_validator

from app.schemas.filters.filter_model import FilterModel
from app.schemas.helpers import spanish_alias, upper_currency


class AmountRange(FilterModel):
    """Inclusive amount range; either end may be open.

    Attributes:
        min: Minimum amount (``minimo``).
        max: Maximum amount (``maximo``).
        currency: ISO 4217 code (``moneda``), upper-cased; ``None`` matches any currency.
    """

    min: Decimal | None = Field(default=None, ge=0, validation_alias=spanish_alias("min", "minimo"))
    max: Decimal | None = Field(default=None, ge=0, validation_alias=spanish_alias("max", "maximo"))
    currency: Annotated[str | None, BeforeValidator(upper_currency)] = Field(
        default=None, pattern=r"^[A-Z]{3}$", validation_alias=spanish_alias("currency", "moneda")
    )

    @model_validator(mode="after")
    def _valid_range(self) -> "AmountRange":
        """Require at least one bound and ``min <= max``.

        Returns:
            The validated range.

        Raises:
            ValueError: If both bounds are missing or the range is reversed.
        """
        if self.min is None and self.max is None:
            raise ValueError("an amount range needs 'minimo' or 'maximo'")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("'minimo' is greater than 'maximo'")
        return self
