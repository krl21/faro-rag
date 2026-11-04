"""Ask an LLM for a JSON object and retry, with a correction, while it is invalid.

Shared by field extraction and question interpretation: both send a prompt,
decode the JSON answer, validate it and, if it is invalid, send the model its
previous answer plus the validation error so it can fix it.
"""

import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from app.ai.extraction.json_output import parse_json_object
from app.ai.extraction.prompts import build_correction_message
from app.ai.providers.base import LLMProvider
from app.ai.providers.types import ChatMessage
from app.core.errors import InvalidLLMOutputError
from app.core.flow_logging import fields
from app.core.retry import retry

logger = logging.getLogger(__name__)


@dataclass
class JsonConversation:
    """Messages of one JSON exchange, updated after each invalid answer.

    Attributes:
        base: Initial prompt (system and user messages).
        messages: Messages to send on the next attempt.
        attempts: LLM calls made so far.
    """

    base: list[ChatMessage]
    messages: list[ChatMessage] = field(default_factory=list)
    attempts: int = 0

    def __post_init__(self) -> None:
        """Start the conversation with the base prompt."""
        self.messages = list(self.base)

    def add_correction(self, answer: str, error: str) -> None:
        """Replace the history with the base prompt, the bad answer and a correction.

        Args:
            answer: Invalid model answer.
            error: Why it was invalid.
        """
        self.messages = [
            *self.base,
            ChatMessage(role="assistant", content=answer),
            build_correction_message(error),
        ]


def complete_json(
    llm: LLMProvider,
    conversation: JsonConversation,
    *,
    purpose: str,
    validate: Callable[[dict[str, Any]], Any],
    delays: Sequence[float],
    sleep: Callable[[float], None] = time.sleep,
) -> Any:
    """Call the LLM until ``validate`` accepts its JSON answer.

    Args:
        llm: Chat provider.
        conversation: Messages to send; updated with corrections on retry.
        purpose: Call label for tracing and the fake provider.
        validate: Validates the decoded JSON; raises ``InvalidLLMOutputError``.
        delays: Seconds to wait before each retry.
        sleep: Wait function (injectable for tests).

    Returns:
        Whatever ``validate`` returns for the first valid answer.

    Raises:
        InvalidLLMOutputError: If every attempt is invalid.
        ProviderError: If the provider fails (not retried here).
    """

    @retry(delays=delays, exceptions=(InvalidLLMOutputError,), sleep=sleep)
    def attempt() -> Any:
        conversation.attempts += 1
        response = llm.complete(conversation.messages, purpose=purpose, json_mode=True)
        try:
            result = validate(parse_json_object(response.text))
        except InvalidLLMOutputError as exc:
            retries_left = len(delays) - conversation.attempts + 1
            logger.warning(
                "invalid llm answer",
                extra=fields(
                    purpose=purpose,
                    attempt=conversation.attempts,
                    retries_left=max(retries_left, 0),
                    error=str(exc),
                ),
            )
            logger.debug(
                "invalid llm answer text", extra=fields(purpose=purpose, answer=response.text)
            )
            conversation.add_correction(response.text, str(exc))
            raise
        logger.debug(
            "valid llm answer", extra=fields(purpose=purpose, attempt=conversation.attempts)
        )
        return result

    return attempt()
