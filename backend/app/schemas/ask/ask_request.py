"""A natural-language question inside a conversation."""

import uuid

from pydantic import BaseModel, Field

from app.schemas.filters import QueryFilters


class AskRequest(BaseModel):
    """A natural-language question inside a conversation.

    Attributes:
        question: The question.
        conversation_id: Conversation to continue; omit it to start a new one.
            Its recent messages give context to interpret the question.
        document_id: Optional document to restrict the answer to.
        filters: Filters to apply instead of interpreting the question (for
            example, the filters of a previous answer edited in the UI).
    """

    question: str = Field(min_length=3, max_length=1000)
    conversation_id: uuid.UUID | None = None
    document_id: uuid.UUID | None = None
    filters: QueryFilters | None = None
