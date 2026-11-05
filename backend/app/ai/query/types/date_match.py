"""A date expression found in a question."""

from dataclasses import dataclass

from app.domain.enums import DateTarget
from app.schemas.filters import DateRange


@dataclass(frozen=True)
class DateMatch:
    """A date expression found in the question.

    Attributes:
        start: First character of the expression.
        end: One past the last character.
        range: Resolved dates.
        target: Upload date or document date.
    """

    start: int
    end: int
    range: DateRange
    target: DateTarget
