"""Questions about one document."""

import logging
import uuid

from fastapi import APIRouter, Request

from app.api.deps import ChatServiceDep
from app.api.mappers import to_ask_response
from app.config import get_settings
from app.core.flow_logging import fields
from app.core.rate_limit import limiter
from app.domain.dtos import PageRange
from app.schemas.ask import AskResponse, DocumentAskRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["ask"])


@router.post(
    "/{document_id}/ask",
    response_model=AskResponse,
    responses={
        404: {"description": "document_not_found or conversation_not_found"},
        409: {"description": "document_not_ready: the document is not processed"},
        429: {"description": "rate_limited"},
    },
)
@limiter.limit(lambda: get_settings().ask_rate_limit)
def ask_document(
    request: Request, document_id: uuid.UUID, body: DocumentAskRequest, chat: ChatServiceDep
) -> AskResponse:
    """Answer a question using only the fragments of one document.

    No filters are interpreted: the hybrid search runs over the chunks of the
    document, optionally within a page range. The question and the answer are
    appended to the conversation. Same rate limit as ``/ask``.

    Args:
        request: Incoming request (required by the rate limiter).
        document_id: Document to ask about.
        body: Question, optional conversation and page range.
        chat: Chat service.

    Returns:
        The answer with citations and the conversation id.
    """
    pages = PageRange(start=body.pages.start, end=body.pages.end) if body.pages else None
    logger.debug(
        "document question received",
        extra=fields(
            document_id=str(document_id),
            question=body.question,
            conversation_id=str(body.conversation_id) if body.conversation_id else None,
            pages=body.pages.model_dump(by_alias=True) if body.pages else None,
        ),
    )
    result = chat.ask_document(
        document_id, body.question, conversation_id=body.conversation_id, pages=pages
    )
    return to_ask_response(result)
