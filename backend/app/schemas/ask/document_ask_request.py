"""Body of ``POST /documents/{id}/ask``."""

import uuid

from pydantic import BaseModel, Field

from app.schemas.ask.page_range_in import PageRangeIn


class DocumentAskRequest(BaseModel):
    """A question about one document.

    Attributes:
        question: The question.
        conversation_id: Conversation to continue; omit it to start a new one.
        pages: Optional page range (``{"from": 2, "to": 5}``) to search in.
    """

    question: str = Field(min_length=3, max_length=1000)
    conversation_id: uuid.UUID | None = None
    pages: PageRangeIn | None = None
