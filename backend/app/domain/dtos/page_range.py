"""An inclusive range of 1-based pages; either end may be open."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PageRange:
    """An inclusive range of 1-based pages; either end may be open.

    Attributes:
        start: First page, or ``None`` for "from the beginning".
        end: Last page, or ``None`` for "to the end".
    """

    start: int | None = None
    end: int | None = None
