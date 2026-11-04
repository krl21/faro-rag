"""One message of a chat conversation sent to the LLM."""

from dataclasses import dataclass
from typing import Literal

from app.ai.providers.types import Attachment

Role = Literal["system", "user", "assistant"]
"""Author of a chat message."""


@dataclass(frozen=True)
class ChatMessage:
    """One message of a chat conversation.

    Attributes:
        role: Author of the message.
        content: Message text.
        attachments: Files sent with the message. Only providers whose model
            accepts files (PDF input) can use them.
    """

    role: Role
    content: str
    attachments: tuple[Attachment, ...] = ()
