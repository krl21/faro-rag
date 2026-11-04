"""Answer to a question."""

import uuid

from pydantic import BaseModel, Field

from app.domain.enums import AskMode
from app.schemas.ask.citation import Citation
from app.schemas.documents import DocumentSummary
from app.schemas.filters import QueryFilters


class AskResponse(BaseModel):
    """Answer to a question.

    Attributes:
        conversation_id: Conversation the question belongs to; send it with
            the next question.
        mode: ``answer`` (RAG answer with citations) or ``list`` (documents
            matching the filters, without calling the LLM).
        answer: Answer text (Spanish) with ``[n]`` citation markers.
        answered: ``False`` when there was not enough evidence to answer.
        citations: Sources referenced by the markers, listed after the answer.
        filters: Filters applied, so the UI can show and edit them.
        filter_source: ``rules``, ``llm``, ``rules_fallback`` or ``explicit``.
        documents: Matching documents when ``mode`` is ``list``.
    """

    conversation_id: uuid.UUID
    mode: AskMode
    answer: str
    answered: bool
    citations: list[Citation]
    filters: QueryFilters
    filter_source: str
    documents: list[DocumentSummary] = Field(default_factory=list)
