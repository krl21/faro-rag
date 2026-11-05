"""Chat use case: interpret a question, filter documents, answer and store the turn."""

import logging
import uuid
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.ai.query.interpreter import QueryInterpreter
from app.ai.rag.answerer import Answerer
from app.ai.rag.field_facts import build_field_facts
from app.core.errors import (
    ConversationNotFoundError,
    DocumentNotFoundError,
    DocumentNotQueryableError,
    DocumentNotReadyError,
)
from app.core.flow_logging import fields
from app.core.telemetry import get_tracer
from app.db.models import Conversation
from app.db.repositories import (
    ConversationRepository,
    DocumentFilterRepository,
    DocumentRepository,
)
from app.db.repositories.document_filters import restrict_ids
from app.domain.dtos import AnswerResult, ChatResult, InterpretedQuery, PageRange
from app.domain.enums import AskMode, ChatRole, DocumentStatus, DocumentType, FilterSource
from app.schemas.filters import QueryFilters

logger = logging.getLogger(__name__)

NO_MATCHING_DOCUMENTS = "No encontré documentos que cumplan esos filtros."
"""Chat message when a listing finds nothing (user-facing, Spanish)."""


def list_message(count: int) -> str:
    """Chat message for a listing (user-facing, Spanish).

    Args:
        count: Documents found.

    Returns:
        The message.
    """
    if count == 0:
        return NO_MATCHING_DOCUMENTS
    if count == 1:
        return "Encontré 1 documento que cumple los filtros."
    return f"Encontré {count} documentos que cumplen los filtros."


class ChatService:
    """Answer chat questions inside persistent conversations."""

    def __init__(
        self,
        session: Session,
        interpreter: QueryInterpreter,
        answerer: Answerer,
        *,
        tz: ZoneInfo,
        context_turns: int,
        list_limit: int,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Create the service.

        Args:
            session: Request session.
            interpreter: Turns questions into filters.
            answerer: RAG answerer.
            tz: Time zone used to resolve relative dates.
            context_turns: Previous exchanges given as context to interpret
                the question (one exchange = question + answer).
            list_limit: Maximum documents returned when listing.
            clock: Current time (injectable for tests).
        """
        self._session = session
        self._conversations = ConversationRepository(session)
        self._documents = DocumentFilterRepository(session, tz)
        self._document_rows = DocumentRepository(session)
        self._interpreter = interpreter
        self._answerer = answerer
        self._tz = tz
        self._context_turns = context_turns
        self._list_limit = list_limit
        self._clock = clock

    def ask(
        self,
        question: str,
        *,
        conversation_id: uuid.UUID | None = None,
        document_id: uuid.UUID | None = None,
        filters: QueryFilters | None = None,
    ) -> ChatResult:
        """Answer a question and store it, with its answer, in the conversation.

        Args:
            question: User question.
            conversation_id: Conversation to continue; ``None`` starts one.
            document_id: Optional document to restrict the answer to.
            filters: Filters sent by the client; skips interpretation.

        Returns:
            The answer or the list of matching documents.

        Raises:
            ConversationNotFoundError: If ``conversation_id`` does not exist.
            ProviderError: If the embedding or LLM provider fails.
        """
        with get_tracer().start_as_current_span("chat.ask") as span:
            conversation = self._conversation(conversation_id)
            span.set_attribute("conversation.id", str(conversation.id))
            now = self._clock()

            interpreted = self._interpret(question, conversation, filters, now)
            result = self._run(question, conversation.id, interpreted, document_id)
            span.set_attribute("chat.mode", result.mode.value)

            self._conversations.append(conversation.id, self._turn(question, result, now))
            self._session.commit()
            logger.info(
                "question answered",
                extra=fields(
                    conversation_id=str(conversation.id),
                    mode=result.mode.value,
                    answered=result.answered,
                    citations=len(result.citations),
                    documents=len(result.documents),
                    filter_source=result.filter_source.value,
                    document_id=str(result.document_id) if result.document_id else None,
                ),
            )
            logger.debug(
                "answer text",
                extra=fields(
                    conversation_id=str(conversation.id),
                    answer=result.answer,
                    citations=[c.model_dump(mode="json") for c in result.citations],
                ),
            )
            return result

    def ask_document(
        self,
        document_id: uuid.UUID,
        question: str,
        *,
        conversation_id: uuid.UUID | None = None,
        pages: PageRange | None = None,
    ) -> ChatResult:
        """Answer a question about one document, optionally within some pages.

        No filters are interpreted (no LLM call for them): the document is
        already chosen, so type, date or amount filters would be redundant or
        contradictory. The hybrid search runs only over that document's chunks,
        and the document's extracted fields (invoice date, amount, policy
        number...) are given to the LLM as citable sources as well, so a
        question about them is answered even when no chunk is similar enough.

        Args:
            document_id: Document to ask about.
            question: User question.
            conversation_id: Conversation to continue; ``None`` starts one.
            pages: Inclusive page range to search in, or ``None`` for all.

        Returns:
            The answer with its citations.

        Raises:
            DocumentNotFoundError: If the document does not exist.
            DocumentNotReadyError: If the document is not processed (``done``).
            DocumentNotQueryableError: If the document is of type ``unknown``.
            ConversationNotFoundError: If ``conversation_id`` does not exist.
            ProviderError: If the embedding or LLM provider fails.
        """
        with get_tracer().start_as_current_span("chat.ask_document") as span:
            span.set_attribute("document.id", str(document_id))
            document = self._document_rows.get(document_id, with_fields=True)
            if document is None:
                raise DocumentNotFoundError(f"Document {document_id} not found")
            if document.status != DocumentStatus.DONE:
                raise DocumentNotReadyError(
                    f"Document {document_id} is {document.status}; "
                    "questions can only be asked once it is processed"
                )
            if document.document_type == DocumentType.UNKNOWN:
                raise DocumentNotQueryableError(
                    f"Document {document_id} is not a policy or an invoice; "
                    "it cannot be used in the chat"
                )
            conversation = self._conversation(conversation_id)
            span.set_attribute("conversation.id", str(conversation.id))
            now = self._clock()

            # The document is known: its extracted fields are citable sources too.
            facts = build_field_facts(document)
            if pages is not None:
                # A page range also limits the fields: only those found inside it.
                facts = [f for f in facts if _in_pages(f.page, pages)]
            answer = self._answerer.answer(question, [document_id], pages=pages, facts=facts)
            print(f"---> answer: {answer}")

            result = ChatResult(
                conversation_id=conversation.id,
                mode=AskMode.ANSWER,
                answer=answer.answer,
                answered=answer.answered,
                citations=answer.citations,
                filters=QueryFilters(),
                filter_source=FilterSource.DOCUMENT,
                document_id=document_id,
                pages=pages,
            )
            self._conversations.append(conversation.id, self._turn(question, result, now))
            self._session.commit()
            logger.info(
                "question answered",
                extra=fields(
                    conversation_id=str(conversation.id),
                    mode=result.mode.value,
                    answered=result.answered,
                    citations=len(result.citations),
                    documents=len(result.documents),
                    filter_source=result.filter_source.value,
                    document_id=str(result.document_id) if result.document_id else None,
                ),
            )
            logger.debug(
                "answer text",
                extra=fields(
                    conversation_id=str(conversation.id),
                    answer=result.answer,
                    citations=[c.model_dump(mode="json") for c in result.citations],
                ),
            )
            return result

    def get_conversation(self, conversation_id: uuid.UUID) -> Conversation:
        """Fetch a conversation.

        Args:
            conversation_id: Conversation identifier.

        Returns:
            The conversation.

        Raises:
            ConversationNotFoundError: If it does not exist.
        """
        conversation = self._conversations.get(conversation_id)
        if conversation is None:
            raise ConversationNotFoundError(f"Conversation {conversation_id} not found")
        return conversation

    def _conversation(self, conversation_id: uuid.UUID | None) -> Conversation:
        """Load the conversation, or create one when no id is given.

        Args:
            conversation_id: Conversation identifier, or ``None``.

        Returns:
            The conversation.

        Raises:
            ConversationNotFoundError: If the id does not exist.
        """
        if conversation_id is None:
            conversation = self._conversations.create()
            self._session.commit()
            logger.info("conversation created", extra=fields(conversation_id=str(conversation.id)))
            return conversation
        return self.get_conversation(conversation_id)

    def _history(self, conversation: Conversation) -> list[tuple[ChatRole, str]]:
        """Return the last exchanges of a conversation, oldest first.

        Args:
            conversation: The conversation.

        Returns:
            Up to ``2 * context_turns`` messages as ``(role, content)``.
        """
        if self._context_turns == 0:
            return []
        recent = conversation.messages[-2 * self._context_turns :]
        return [(ChatRole(m["role"]), m["content"]) for m in recent]

    def _interpret(
        self,
        question: str,
        conversation: Conversation,
        filters: QueryFilters | None,
        now: datetime,
    ) -> InterpretedQuery:
        """Get the filters: the client's, or the interpreted ones.

        Args:
            question: User question.
            conversation: Current conversation.
            filters: Filters sent by the client.
            now: Current time.

        Returns:
            The filters and their source.
        """
        if filters is not None:
            return InterpretedQuery(filters, FilterSource.EXPLICIT)
        today: date = now.astimezone(self._tz).date()
        return self._interpreter.interpret(question, self._history(conversation), today)

    def _run(
        self,
        question: str,
        conversation_id: uuid.UUID,
        interpreted: InterpretedQuery,
        document_id: uuid.UUID | None,
    ) -> ChatResult:
        """List the matching documents or answer with RAG inside them.

        A question with filters and nothing else to ask (``necesito las
        facturas de ayer``) is a listing: it never calls the LLM.

        Args:
            question: User question.
            conversation_id: Conversation identifier.
            interpreted: Filters and their source.
            document_id: Optional document restriction.

        Returns:
            The result.
        """
        filters = interpreted.filters
        if filters.has_restrictions and not filters.query:
            documents = self._documents.matching_documents(filters, self._list_limit)
            if document_id is not None:
                documents = [d for d in documents if d.id == document_id]
            logger.info(
                "documents listed by filters",
                extra=fields(matching=len(documents), limit=self._list_limit),
            )
            logger.debug(
                "listed documents", extra=fields(document_ids=[str(d.id) for d in documents])
            )
            return ChatResult(
                conversation_id=conversation_id,
                mode=AskMode.LIST,
                answer=list_message(len(documents)),
                answered=bool(documents),
                citations=[],
                filters=filters,
                filter_source=interpreted.source,
                documents=documents,
            )

        matching = self._documents.matching_ids(filters) if filters.has_restrictions else None
        logger.info(
            "documents restricted by filters",
            extra=fields(
                matching=None if matching is None else len(matching),
                document_id=str(document_id) if document_id else None,
            ),
        )
        answer: AnswerResult = self._answerer.answer(
            question,
            restrict_ids(matching, document_id),
            search_text=filters.query or None,
        )
        return ChatResult(
            conversation_id=conversation_id,
            mode=AskMode.ANSWER,
            answer=answer.answer,
            answered=answer.answered,
            citations=answer.citations,
            filters=filters,
            filter_source=interpreted.source,
        )

    @staticmethod
    def _turn(question: str, result: ChatResult, now: datetime) -> list[dict[str, Any]]:
        """Build the two messages stored for one question.

        Args:
            question: User question.
            result: Its answer.
            now: Current time.

        Returns:
            The user message and the assistant message, JSON-serializable.
        """
        timestamp = now.isoformat()
        details = {
            "mode": result.mode.value,
            "answered": result.answered,
            "filters": result.filters.model_dump(mode="json"),
            "filter_source": result.filter_source.value,
            "citations": [c.model_dump(mode="json") for c in result.citations],
            "document_ids": [str(d.id) for d in result.documents],
        }
        if result.document_id is not None:
            details["document_id"] = str(result.document_id)
        if result.pages is not None:
            details["pages"] = {"from": result.pages.start, "to": result.pages.end}
        return [
            {"role": ChatRole.USER.value, "content": question, "created_at": timestamp},
            {
                "role": ChatRole.ASSISTANT.value,
                "content": result.answer,
                "created_at": timestamp,
                "details": details,
            },
        ]


def _in_pages(page: int | None, pages: PageRange) -> bool:
    """Tell whether a page falls inside an inclusive range.

    Args:
        page: 1-based page, or ``None`` when unknown.
        pages: Range; either end may be open.

    Returns:
        ``False`` for an unknown page, so a page-restricted question never
        relies on a field that may come from outside the range.
    """
    if page is None:
        return False
    return (pages.start is None or page >= pages.start) and (pages.end is None or page <= pages.end)
