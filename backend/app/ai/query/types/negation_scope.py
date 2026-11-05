"""A negated part of a question."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NegationScope:
    """A negated part of the question.

    Attributes:
        trigger_start: Start of the negation word.
        trigger_end: End of the negation word.
        end: End of the scope (end of the clause).
    """

    trigger_start: int
    trigger_end: int
    end: int

    def contains(self, position: int) -> bool:
        """Tell whether a position falls inside the scope.

        Args:
            position: Character position.

        Returns:
            ``True`` when the position is after the trigger and before the end.
        """
        return self.trigger_end <= position < self.end
