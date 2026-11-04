"""FastAPI dependencies."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.ai.providers.factory import get_embedding_provider, get_llm_provider
from app.ai.query.interpreter import QueryInterpreter
from app.ai.query.llm_parser import LLMQueryParser
from app.ai.rag.answerer import Answerer
from app.ai.rag.retriever import HybridRetriever
from app.config import Settings, get_settings
from app.db.repositories import ChunkRepository
from app.db.session import SessionLocal
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService
from app.services.field_edit_service import FieldEditService
from app.services.storage import LocalStorage
from app.worker.tasks import enqueue_document


def get_session() -> Iterator[Session]:
    """Provide a database session per request.

    Yields:
        A session closed when the request ends. Services commit explicitly.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_document_service(session: SessionDep, settings: SettingsDep) -> DocumentService:
    """Build the document service for a request.

    Args:
        session: Request session.
        settings: Application settings.

    Returns:
        The document service.
    """
    return DocumentService(session, LocalStorage(settings.storage_dir), enqueue_document)


def get_answerer(session: SessionDep, settings: SettingsDep) -> Answerer:
    """Build the RAG answerer for a request.

    Args:
        session: Request session.
        settings: Application settings.

    Returns:
        The answerer.
    """
    retriever = HybridRetriever(
        ChunkRepository(session),
        get_embedding_provider(),
        top_k=settings.retrieval_top_k,
        candidates=settings.retrieval_candidates,
        min_similarity=settings.retrieval_min_similarity,
        rrf_k=settings.retrieval_rrf_k,
    )
    return Answerer(retriever, get_llm_provider())


def get_chat_service(session: SessionDep, settings: SettingsDep) -> ChatService:
    """Build the chat service for a request.

    Args:
        session: Request session.
        settings: Application settings.

    Returns:
        The chat service.
    """
    interpreter = QueryInterpreter(
        LLMQueryParser(
            get_llm_provider(),
            timezone=settings.timezone,
            retry_delays=settings.extraction_retry_delays,
        )
    )
    return ChatService(
        session,
        interpreter,
        get_answerer(session, settings),
        tz=settings.tzinfo,
        context_turns=settings.chat_context_turns,
        list_limit=settings.chat_list_limit,
    )


def get_field_edit_service(session: SessionDep) -> FieldEditService:
    """Build the field edit service for a request.

    Args:
        session: Request session.

    Returns:
        The field edit service.
    """
    return FieldEditService(session)


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]
FieldEditServiceDep = Annotated[FieldEditService, Depends(get_field_edit_service)]
AnswererDep = Annotated[Answerer, Depends(get_answerer)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
