"""A conversation with all its messages."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.conversations.conversation_message import ConversationMessage


class ConversationDetail(BaseModel):
    """A conversation with all its messages.

    Attributes:
        id: Conversation identifier.
        messages: Messages, oldest first.
        created_at: Creation time.
        updated_at: Time of the last message.
    """

    id: uuid.UUID
    messages: list[ConversationMessage]
    created_at: datetime
    updated_at: datetime
