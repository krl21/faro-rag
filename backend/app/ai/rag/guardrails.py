"""Checks applied to the model's answer before it reaches the user."""

import re

from app.ai.rag.prompt_builder import NO_EVIDENCE_TOKEN
from app.ai.rag.types import CheckedAnswer

_CITATION = re.compile(r"\[(\d{1,3})\]")


def check_answer(text: str, fragment_count: int) -> CheckedAnswer:
    """Validate the citations of a generated answer.

    An answer is rejected (``has_evidence=False``) when the model reports
    ``NO_EVIDENCE`` or when it does not cite any of the provided fragments:
    an uncited answer cannot be verified, so it is treated as invented.
    Citation numbers that do not correspond to a provided fragment are removed.

    The model cites fragments by their position in the prompt (``[5]`` is the
    fifth fragment sent), so the numbers can skip values. They are renumbered
    by order of first appearance: the first cited fragment becomes ``[1]``,
    the next new one ``[2]``... and a fragment cited twice keeps its number.
    With ``n`` citations, no marker is greater than ``n``.

    Args:
        text: Raw model answer.
        fragment_count: Number of fragments given to the model.

    Returns:
        The checked answer.
    """
    stripped = text.strip()
    if not stripped or NO_EVIDENCE_TOKEN in stripped:
        return CheckedAnswer(text="", cited=[], has_evidence=False)

    new_numbers: dict[int, int] = {}  # Fragment number -> citation marker.

    def renumber(match: re.Match[str]) -> str:
        fragment = int(match.group(1))
        if not 1 <= fragment <= fragment_count:
            return ""
        if fragment not in new_numbers:
            new_numbers[fragment] = len(new_numbers) + 1
        return f"[{new_numbers[fragment]}]"

    cleaned = _CITATION.sub(renumber, stripped).strip()
    cited = list(new_numbers)  # Insertion order = order of first appearance.
    return CheckedAnswer(text=cleaned, cited=cited, has_evidence=bool(cited))
