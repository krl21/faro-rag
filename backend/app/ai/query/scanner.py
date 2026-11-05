"""Working copy of a question for the rule-based parser.

Matchers run on a folded, lower-case copy of the question (``Pólizas`` ->
``polizas``) with the same length as the original, so positions map back to
the original text (needed to check upper case). Every match is *consumed*:
its characters are blanked so later matchers cannot match them again, and
its span is removed from the text left for the semantic search.
"""

import re
from collections.abc import Iterator

from app.core.text_normalization import fold


class QuestionScanner:
    """Hold the original question, its searchable copy and the consumed spans."""

    def __init__(self, question: str) -> None:
        """Create the scanner.

        Args:
            question: The user question, as typed.
        """
        self.original = question
        folded = fold(question).lower()
        # ``lower`` can change the length of a few exotic characters; keep the
        # original folded text in that case so positions still line up.
        self._text = folded if len(folded) == len(question) else fold(question)
        self.consumed: list[tuple[int, int]] = []

    @property
    def text(self) -> str:
        """Folded, lower-case text with consumed spans blanked.

        Returns:
            The searchable text.
        """
        return self._text

    def finditer(self, pattern: re.Pattern[str]) -> Iterator[re.Match[str]]:
        """Search the current (masked) text.

        Args:
            pattern: Compiled pattern written for folded lower-case text.

        Returns:
            The matches, in order.
        """
        return pattern.finditer(self._text)

    def consume(self, start: int, end: int) -> None:
        """Mark a span as used by a filter.

        Args:
            start: First character.
            end: One past the last character.
        """
        self._text = self._text[:start] + " " * (end - start) + self._text[end:]
        self.consumed.append((start, end))

    def is_upper(self, start: int, end: int) -> bool:
        """Tell whether the original text of a span is written in upper case.

        Args:
            start: First character.
            end: One past the last character.

        Returns:
            ``True`` when the span has letters and all of them are upper case.
        """
        fragment = self.original[start:end]
        return any(c.isalpha() for c in fragment) and fragment == fragment.upper()

    def remaining(self) -> str:
        """Return the original question without the consumed spans.

        Returns:
            The leftover text with single spaces.
        """
        chars = list(self.original)
        for start, end in self.consumed:
            chars[start:end] = " " * (end - start)
        return " ".join("".join(chars).split())
