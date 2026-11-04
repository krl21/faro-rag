"""Checks run when a process starts."""

import logging

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.ai.providers.base import EmbeddingProvider
from app.config import LLMProviderName, Settings
from app.db.repositories import ChunkRepository
from app.domain.enums import DocumentInput

logger = logging.getLogger(__name__)


def check_embedding_dimension(
    settings: Settings, provider: EmbeddingProvider, engine: Engine
) -> bool:
    """Compare the provider, ``EMBEDDING_DIM`` and the database column dimensions.

    The result is logged at ``INFO`` when everything matches and at ``ERROR``
    otherwise. A mismatch means the model was changed without recreating the
    ``chunks`` table and reprocessing the documents.

    Args:
        settings: Application settings.
        provider: Configured embedding provider.
        engine: Database engine.

    Returns:
        ``True`` when the three dimensions match.
    """
    try:
        provider_dim = provider.dimension
        with Session(engine) as session:
            column_dim = ChunkRepository(session).embedding_column_dimension()
    except Exception as exc:
        logger.error("embedding dimension check could not run", extra={"error": str(exc)})
        return False

    details = {
        "embedding_model": provider.model,
        "provider_dim": provider_dim,
        "configured_dim": settings.embedding_dim,
        "database_dim": column_dim,
    }
    if provider_dim == settings.embedding_dim == column_dim:
        logger.info("embedding dimension check passed", extra=details)
        return True
    logger.error(
        "embedding dimension mismatch: recreate the chunks table and reprocess documents",
        extra=details,
    )
    return False


def check_pdf_input(settings: Settings) -> bool:
    """Check whether the configured LLM accepts PDF input.

    With ``LLM_DOCUMENT_INPUT=pdf`` both LLM calls send the whole PDF, so the
    model must accept files. The answer comes from LiteLLM's model map, which
    can lag behind the providers, so a negative result is only a warning and
    never blocks startup.

    Args:
        settings: Application settings.

    Returns:
        ``True`` when the model is known to accept PDFs, when the document is
        sent as text (no PDF input needed) and always for the fake provider,
        which reads the PDF locally.
    """
    if settings.llm_document_input is DocumentInput.TEXT:
        logger.info(
            "pdf input check skipped: documents are sent as text",
            extra={"llm_model": settings.llm_model},
        )
        return True
    if settings.llm_provider is not LLMProviderName.LITELLM:
        logger.info("pdf input check passed", extra={"llm_model": settings.llm_model})
        return True
    try:
        from litellm.utils import supports_pdf_input

        supported = bool(supports_pdf_input(model=settings.llm_model))
    except Exception as exc:
        logger.warning("pdf input check could not run", extra={"error": str(exc)})
        return False
    if supported:
        logger.info("pdf input check passed", extra={"llm_model": settings.llm_model})
    else:
        logger.warning(
            "LLM may not accept PDF input: set LLM_DOCUMENT_INPUT=text for this model",
            extra={"llm_model": settings.llm_model},
        )
    return supported
