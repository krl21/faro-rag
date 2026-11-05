"""Decide the filters of a question: rules first, the LLM only when needed."""

import logging
from collections.abc import Sequence
from datetime import date

from app.ai.query.llm_parser import LLMQueryParser
from app.ai.query.rule_parser import parse_with_rules
from app.core.flow_logging import fields
from app.core.telemetry import get_tracer
from app.domain.dtos import InterpretedQuery
from app.domain.enums import ChatRole, FilterSource

logger = logging.getLogger(__name__)


class QueryInterpreter:
    """Turn a question into filters, minimizing LLM calls."""

    def __init__(self, llm_parser: LLMQueryParser) -> None:
        """Create the interpreter.

        Args:
            llm_parser: LLM fallback.
        """
        self._llm_parser = llm_parser

    def interpret(
        self, question: str, history: Sequence[tuple[ChatRole, str]], today: date
    ) -> InterpretedQuery:
        """Extract the filters of a question.

        The rules run first. The LLM (with the recent history) is called only
        if the rules report something unresolved: a negation without a clear
        target, unknown date words, a person or company name, or a reference
        to earlier messages.

        Args:
            question: Current user question.
            history: Previous messages, oldest first.
            today: Current date in the configured time zone.

        Returns:
            The filters and their source.

        Raises:
            ProviderError: If the LLM provider fails.
        """
        with get_tracer().start_as_current_span("chat.interpret") as span:
            rules = parse_with_rules(question, today, has_history=bool(history))
            span.set_attribute("query.unresolved", [u.value for u in rules.unresolved])
            if not rules.unresolved:
                result = InterpretedQuery(rules.filters, FilterSource.RULES)
            else:
                llm_filters = self._llm_parser.parse(question, history, today)
                source = FilterSource.LLM if llm_filters else FilterSource.RULES_FALLBACK
                result = InterpretedQuery(llm_filters or rules.filters, source, rules.unresolved)
            span.set_attribute("query.filter_source", result.source.value)
            span.set_attribute("query.has_restrictions", result.filters.has_restrictions)
            logger.info(
                "question interpreted",
                extra=fields(
                    filter_source=result.source.value,
                    unresolved=[u.value for u in result.unresolved],
                    has_restrictions=result.filters.has_restrictions,
                    history_messages=len(history),
                ),
            )
            logger.debug(
                "interpreted filters",
                extra=fields(
                    question=question,
                    rule_filters=rules.filters.model_dump(mode="json"),
                    filters=result.filters.model_dump(mode="json"),
                ),
            )
            return result
