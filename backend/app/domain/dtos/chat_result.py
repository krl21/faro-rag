"""Outcome of one chat question."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.domain.dtos.page_range import PageRange
from app.domain.enums import AskMode, FilterSource

if TYPE_CHECKING:
    from app.db.models import Document
    from app.schemas.ask import Citation
    from app.schemas.filters import QueryFilters


@dataclass(frozen=True)
class ChatResult:
    """Outcome of one question.

    Attributes:
        conversation_id: Conversation the question belongs to.
        mode: ``answer`` or ``list``.
        answer: Text shown in the chat.
        answered: Whether there was evidence (or matching documents).
        citations: Sources of the answer.
        filters: Filters applied.
        filter_source: Where the filters came from.
        documents: Matching documents when listing.
        document_id: Document the question was restricted to, if any.
        pages: Pages the question was restricted to, if any.
    """

    conversation_id: uuid.UUID
    mode: AskMode
    answer: str
    answered: bool
    citations: list[Citation]
    filters: QueryFilters
    filter_source: FilterSource
    documents: list[Document] = field(default_factory=list)
    document_id: uuid.UUID | None = None
    pages: PageRange | None = None
