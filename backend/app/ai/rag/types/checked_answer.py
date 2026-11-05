"""LLM answer after the citation guardrails."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckedAnswer:
    """An answer after the guardrails.

    Attributes:
        text: Answer text with invalid citation markers removed and the valid
            ones renumbered ``[1]``, ``[2]``... by order of first appearance.
        cited: Fragment numbers (position in the prompt) of each citation:
            marker ``[i]`` in ``text`` refers to fragment ``cited[i - 1]``.
        has_evidence: ``False`` when the answer must be replaced by the
            "not enough information" message.
    """

    text: str
    cited: list[int]
    has_evidence: bool
