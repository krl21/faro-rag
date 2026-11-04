"""Inclusive date range; either end may be open."""

from datetime import date

from pydantic import Field, model_validator

from app.schemas.filters.filter_model import FilterModel
from app.schemas.helpers import spanish_alias


class DateRange(FilterModel):
    """Inclusive date range; either end may be open.

    Attributes:
        start: First day (``desde``).
        end: Last day (``hasta``).
    """

    start: date | None = Field(default=None, validation_alias=spanish_alias("start", "desde"))
    end: date | None = Field(default=None, validation_alias=spanish_alias("end", "hasta"))

    @model_validator(mode="after")
    def _valid_range(self) -> "DateRange":
        """Require at least one end and ``start <= end``.

        Returns:
            The validated range.

        Raises:
            ValueError: If both ends are missing or the range is reversed.
        """
        if self.start is None and self.end is None:
            raise ValueError("a date range needs 'desde' or 'hasta'")
        if self.start and self.end and self.start > self.end:
            raise ValueError("'desde' is after 'hasta'")
        return self
