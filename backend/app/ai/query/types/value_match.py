"""An identifier found in a question."""

from dataclasses import dataclass

from app.domain.enums import FilterField


@dataclass(frozen=True)
class ValueMatch:
    """A value found in the question.

    Attributes:
        start: First character of the expression (label included).
        end: One past the last character.
        field: Field the value belongs to.
        values: Values as written by the user (original case).
    """

    start: int
    end: int
    field: FilterField
    values: tuple[str, ...]
