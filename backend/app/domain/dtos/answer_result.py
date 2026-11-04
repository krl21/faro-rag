"""Answer produced by the RAG pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.ask import Citation


@dataclass(frozen=True)
class AnswerResult:
    """Answer produced by the RAG pipeline.

    Attributes:
        answer: Answer text (Spanish) with ``[n]`` citation markers.
        answered: ``False`` when there was not enough evidence to answer.
        citations: Sources referenced by the markers.
    """

    answer: str
    answered: bool
    citations: list[Citation] = field(default_factory=list)
