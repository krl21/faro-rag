"""Conversation endpoints."""

import logging
import uuid

from fastapi import APIRouter

from app.api.deps import ChatServiceDep
from app.api.mappers import to_conversation
from app.core.flow_logging import fields
from app.schemas.conversations import ConversationDetail

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(conversation_id: uuid.UUID, chat: ChatServiceDep) -> ConversationDetail:
    """Return a conversation with all its messages.

    Args:
        conversation_id: Conversation identifier.
        chat: Chat service.

    Returns:
        The conversation, oldest message first.
    """
    logger.debug("conversation requested", extra=fields(conversation_id=str(conversation_id)))
    return to_conversation(chat.get_conversation(conversation_id))
