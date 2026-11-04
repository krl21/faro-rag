"""Policy validity period."""

from datetime import date

from pydantic import Field, model_validator

from app.schemas.extraction.spanish_input import SpanishInput


class Validity(SpanishInput):
    """Policy validity period.

    Attributes:
        start: First day of coverage (``inicio``).
        end: Last day of coverage (``fin``).
    """

    start: date = Field(alias="inicio")
    end: date = Field(alias="fin")

    @model_validator(mode="after")
    def _end_after_start(self) -> "Validity":
        """Reject periods that end before they start.

        Returns:
            The validated period.

        Raises:
            ValueError: If ``end`` is before ``start``.
        """
        if self.end < self.start:
            raise ValueError("validity end date is before its start date")
        return self
