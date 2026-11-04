"""Convert ORM objects into API response models."""

from app.ai.extraction.field_specs import find_spec
from app.db.models import Conversation, Document, ExtractedField
from app.schemas.ask import AskResponse
from app.schemas.conversations import ConversationDetail, ConversationMessage
from app.schemas.documents import (
    DocumentDetail,
    DocumentError,
    DocumentSummary,
    ExtractedFieldOut,
)
from app.services.chat_service import ChatResult


def _error(document: Document) -> DocumentError | None:
    """Build the error object of a document.

    Args:
        document: The document.

    Returns:
        The error, or ``None`` when there is none.
    """
    if document.error_code is None:
        return None
    return DocumentError(code=document.error_code, message=document.error_message or "")


def to_summary(document: Document) -> DocumentSummary:
    """Map a document to its list representation.

    Args:
        document: The document.

    Returns:
        The summary model.
    """
    return DocumentSummary(
        id=document.id,
        filename=document.filename,
        status=document.status,
        document_type=document.document_type,
        page_count=document.page_count,
        size_bytes=document.size_bytes,
        error=_error(document),
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def to_field_out(field: ExtractedField, document_type: str | None) -> ExtractedFieldOut:
    """Map a stored field, adding its value type and whether it can be edited.

    Args:
        field: The stored field.
        document_type: Type of its document (decides the field definition).

    Returns:
        The field model.
    """
    spec = find_spec(document_type, field.name)
    out = ExtractedFieldOut(
        name=field.name,
        value=field.value,
        confidence=field.confidence,
        status=field.status,
        error=field.error,
        attempts=field.attempts,
        page=field.page,
        original_value=field.original_value,
        edited_at=field.edited_at,
        editable=spec is not None,
    )
    if spec is not None:
        out.value_type = spec.value_type
    return out


def to_detail(document: Document, chunk_count: int) -> DocumentDetail:
    """Map a document to its detailed representation.

    Args:
        document: The document, with its fields loaded.
        chunk_count: Number of stored chunks.

    Returns:
        The detail model.
    """
    return DocumentDetail(
        **to_summary(document).model_dump(),
        chunk_count=chunk_count,
        fields=[to_field_out(f, document.document_type) for f in document.fields],
    )


def to_ask_response(result: ChatResult) -> AskResponse:
    """Map a chat result to the ``POST /ask`` response.

    Args:
        result: Outcome of the question.

    Returns:
        The response model.
    """
    return AskResponse(
        conversation_id=result.conversation_id,
        mode=result.mode,
        answer=result.answer,
        answered=result.answered,
        citations=result.citations,
        filters=result.filters,
        filter_source=result.filter_source.value,
        documents=[to_summary(d) for d in result.documents],
    )


def to_conversation(conversation: Conversation) -> ConversationDetail:
    """Map a conversation to its API representation.

    Args:
        conversation: The conversation.

    Returns:
        The conversation with its messages.
    """
    return ConversationDetail(
        id=conversation.id,
        messages=[ConversationMessage.model_validate(m) for m in conversation.messages],
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )
