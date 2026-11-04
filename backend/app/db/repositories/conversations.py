"""Repository for ``Conversation`` rows."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import bindparam, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.db.models import Conversation


class ConversationRepository:
    """Create conversations and append their messages."""

    def __init__(self, session: Session) -> None:
        """Create the repository.

        Args:
            session: Active SQLAlchemy session.
        """
        self._session = session

    def create(self) -> Conversation:
        """Create an empty conversation.

        Returns:
            The new conversation (flushed, so it has its id).
        """
        conversation = Conversation(messages=[])
        self._session.add(conversation)
        self._session.flush()
        return conversation

    def get(self, conversation_id: uuid.UUID) -> Conversation | None:
        """Fetch a conversation.

        Args:
            conversation_id: Conversation identifier.

        Returns:
            The conversation, or ``None`` if it does not exist.
        """
        return self._session.get(Conversation, conversation_id)

    def append(self, conversation_id: uuid.UUID, messages: Sequence[dict[str, Any]]) -> None:
        """Append messages in one atomic ``UPDATE``.

        ``messages = messages || :new`` runs inside PostgreSQL, so two questions
        sent at the same time to the same conversation never overwrite each
        other's messages (no read-modify-write in Python).

        Args:
            conversation_id: Conversation identifier.
            messages: JSON-serializable messages, oldest first.
        """
        self._session.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(
                # Typed parameter: serialized once as a JSON array (a cast of a
                # json.dumps() string would store each message as a string).
                messages=Conversation.messages.op("||")(
                    bindparam("new_messages", list(messages), type_=JSONB)
                ),
                updated_at=datetime.now(UTC),
            )
            .execution_options(synchronize_session=False)
        )
        self._session.expire_all()
