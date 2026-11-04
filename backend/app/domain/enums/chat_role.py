"""Author of a conversation message."""

from enum import StrEnum


class ChatRole(StrEnum):
    """Author of a conversation message."""

    USER = "user"
    ASSISTANT = "assistant"
