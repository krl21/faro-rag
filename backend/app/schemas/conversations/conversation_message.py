"""One message of a conversation."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.domain.enums import ChatRole


class ConversationMessage(BaseModel):
    """One message of a conversation.

    Attributes:
        role: ``user`` or ``assistant``.
        content: Message text.
        created_at: When it was stored.
        details: For assistant messages: mode, filters and citations.
    """

    role: ChatRole
    content: str
    created_at: datetime
    details: dict[str, Any] | None = None
