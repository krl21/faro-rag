"""Response models for the ``/conversations`` endpoints.

One module per class; this package re-exports the public names.
"""

from app.schemas.conversations.conversation_detail import ConversationDetail
from app.schemas.conversations.conversation_message import ConversationMessage

__all__ = ["ConversationDetail", "ConversationMessage"]
