"""Amount range found in a question."""

from dataclasses import dataclass

from app.schemas.filters import AmountRange


@dataclass(frozen=True)
class AmountMatch:
    """Amount range found in the question, with the spans it consumed.

    Attributes:
        range: Resolved range.
        spans: ``(start, end)`` of each expression used.
    """

    range: AmountRange
    spans: list[tuple[int, int]]
