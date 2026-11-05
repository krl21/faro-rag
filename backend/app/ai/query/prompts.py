"""Spanish prompt that turns a chat question into structured filters.

The texts live in ``app/ai/prompts/query/*.txt`` and are loaded once, here.
"""

from collections.abc import Sequence
from datetime import date

from app.ai.prompt_loader import load_prompt, render
from app.ai.providers.types import ChatMessage
from app.ai.sanitization import sanitize_untrusted
from app.domain.enums import ChatRole

MAX_HISTORY_MESSAGE_CHARS = 1000
"""Long answers are cut: only their gist is needed to resolve references."""

# Loaded once, when the module is imported (texts in app/ai/prompts/query/).
QUERY_SYSTEM = load_prompt("query/system.txt").template
_USER = load_prompt("query/user.txt")
_USER_NO_HISTORY = load_prompt("query/user_no_history.txt")
_HISTORY_MESSAGE = load_prompt("query/history_message.txt")

_ROLE_LABELS = {ChatRole.USER: "usuario", ChatRole.ASSISTANT: "asistente"}


def build_query_messages(
    question: str,
    history: Sequence[tuple[ChatRole, str]],
    today: date,
    timezone: str,
) -> list[ChatMessage]:
    """Build the prompt that extracts filters from a question.

    Args:
        question: Current user question.
        history: Previous messages, oldest first, as ``(role, content)``.
        today: Current date in the configured time zone.
        timezone: IANA name of that time zone.

    Returns:
        System and user messages.
    """
    lines = [
        render(
            _HISTORY_MESSAGE,
            role=_ROLE_LABELS[role],
            content=sanitize_untrusted(content)[:MAX_HISTORY_MESSAGE_CHARS],
        )
        for role, content in history
    ]
    values = {
        "today": today.isoformat(),
        "timezone": timezone,
        "question": sanitize_untrusted(question),
    }
    if lines:
        user = render(_USER, history="\n".join(lines), **values)
    else:
        user = render(_USER_NO_HISTORY, **values)
    return [
        ChatMessage(role="system", content=QUERY_SYSTEM),
        ChatMessage(role="user", content=user),
    ]
