"""LLM fallback that turns a question (plus recent history) into filters."""

import logging
import time
from collections.abc import Callable, Sequence
from datetime import date
from typing import Any

from pydantic import ValidationError

from app.ai.extraction.field_validation import format_errors
from app.ai.json_conversation import JsonConversation, complete_json
from app.ai.providers.base import LLMProvider
from app.ai.query.prompts import build_query_messages
from app.core.errors import InvalidLLMOutputError
from app.domain.enums import ChatRole
from app.schemas.filters import QueryFilters

logger = logging.getLogger(__name__)

QUERY_PURPOSE = "parse_query"


class LLMQueryParser:
    """Ask the LLM for the filters of a question, validated with Pydantic."""

    def __init__(
        self,
        llm: LLMProvider,
        *,
        timezone: str,
        retry_delays: Sequence[float],
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """Create the parser.

        Args:
            llm: Chat provider.
            timezone: IANA zone name, given to the model to resolve dates.
            retry_delays: Seconds to wait before each retry of an invalid answer.
            sleep: Wait function (injectable for tests).
        """
        self._llm = llm
        self._timezone = timezone
        self._delays = tuple(retry_delays)
        self._sleep = sleep

    def parse(
        self, question: str, history: Sequence[tuple[ChatRole, str]], today: date
    ) -> QueryFilters | None:
        """Extract the filters of a question.

        Args:
            question: Current user question.
            history: Previous messages, oldest first.
            today: Current date in the configured time zone.

        Returns:
            The filters, or ``None`` if every answer was invalid (the caller
            then falls back to the rule-based filters).

        Raises:
            ProviderError: If the LLM provider fails.
        """
        conversation = JsonConversation(
            build_query_messages(question, history, today, self._timezone)
        )

        def validate(data: dict[str, Any]) -> QueryFilters:
            try:
                return QueryFilters.model_validate(data)
            except ValidationError as exc:
                raise InvalidLLMOutputError(format_errors(exc)) from exc

        try:
            return complete_json(
                self._llm,
                conversation,
                purpose=QUERY_PURPOSE,
                validate=validate,
                delays=self._delays,
                sleep=self._sleep,
            )
        except InvalidLLMOutputError as exc:
            logger.warning(
                "query filters from the LLM are invalid, using the rule-based ones",
                extra={"attempts": conversation.attempts, "error": str(exc)},
            )
            return None
