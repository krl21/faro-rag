"""Question answering endpoint (chat with filters and RAG)."""

import logging

from fastapi import APIRouter, Request

from app.api.deps import ChatServiceDep
from app.api.mappers import to_ask_response
from app.config import get_settings
from app.core.flow_logging import fields
from app.core.rate_limit import limiter
from app.schemas.ask import AskRequest, AskResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ask"])


@router.post("/ask", response_model=AskResponse)
# A callable is evaluated on every request, so the limit follows the settings.
@limiter.limit(lambda: get_settings().ask_rate_limit)
def ask(request: Request, body: AskRequest, chat: ChatServiceDep) -> AskResponse:
    """Answer a question inside a conversation.

    The question is turned into filters (type, dates, amount, identifiers to
    include or exclude). With filters only, the matching documents are listed
    without calling the LLM; otherwise the answer uses only the fragments of
    the matching documents, with citations. The question and the answer are
    appended to the conversation. Rate limited per client IP (``ASK_RATE_LIMIT``).

    Args:
        request: Incoming request (required by the rate limiter).
        body: Question, optional conversation, document and filters.
        chat: Chat service.

    Returns:
        The answer, its citations, the applied filters and the conversation id.
    """
    logger.debug(
        "question received",
        extra=fields(
            question=body.question,
            conversation_id=str(body.conversation_id) if body.conversation_id else None,
            document_id=str(body.document_id) if body.document_id else None,
            filters=body.filters.model_dump(mode="json") if body.filters else None,
        ),
    )
    result = chat.ask(
        body.question,
        conversation_id=body.conversation_id,
        document_id=body.document_id,
        filters=body.filters,
    )
    return to_ask_response(result)
