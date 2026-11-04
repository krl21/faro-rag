"""Celery tasks."""

import logging
import uuid
from functools import lru_cache

from celery import Task
from sqlalchemy.exc import OperationalError

from app.ai.extraction.field_extractor import FieldExtractor
from app.ai.ingestion.pdf_extractor import build_pdf_extractor
from app.ai.providers.factory import get_embedding_provider, get_llm_provider
from app.config import get_settings
from app.core.errors import ProviderError
from app.core.flow_logging import fields, log_step
from app.services.document_processor import DocumentProcessor
from app.services.storage import LocalStorage
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)

_settings = get_settings()

UNEXPECTED_ERROR_CODE = "processing_error"


@lru_cache
def get_processor() -> DocumentProcessor:
    """Build the document processor once per worker process.

    Returns:
        The shared processor.
    """
    settings = get_settings()
    return DocumentProcessor(
        settings=settings,
        storage=LocalStorage(settings.storage_dir),
        extractor=build_pdf_extractor(settings),
        embeddings=get_embedding_provider(),
        field_extractor=FieldExtractor(
            get_llm_provider(),
            retry_delays=settings.extraction_retry_delays,
            classification_max_chars=settings.classification_max_chars,
            document_input=settings.llm_document_input,
        ),
    )


class ProcessDocumentTask(Task):
    """Base task that stores the error on the document when retries run out."""

    def on_retry(self, exc, task_id, args, kwargs, einfo) -> None:
        """Log that a transient failure will be retried with backoff.

        Args:
            exc: Exception raised by the attempt.
            task_id: Celery task id.
            args: Positional task arguments (``document_id``).
            kwargs: Keyword task arguments.
            einfo: Exception info.
        """
        logger.warning(
            "document task will be retried",
            extra=fields(
                document_id=str(args[0] if args else kwargs.get("document_id")),
                task_id=task_id,
                attempt=self.request.retries + 1,
                max_retries=self.max_retries,
                error_type=type(exc).__name__,
                error=str(exc),
            ),
        )

    def on_failure(self, exc, task_id, args, kwargs, einfo) -> None:
        """Mark the document as failed after the final attempt.

        Args:
            exc: Exception raised by the last attempt.
            task_id: Celery task id.
            args: Positional task arguments (``document_id``).
            kwargs: Keyword task arguments.
            einfo: Exception info.
        """
        document_id = uuid.UUID(str(args[0] if args else kwargs["document_id"]))
        code = getattr(exc, "code", UNEXPECTED_ERROR_CODE)
        logger.error(
            "document task failed",
            extra=fields(
                document_id=str(document_id),
                task_id=task_id,
                error_code=code,
                error_type=type(exc).__name__,
                error=str(exc),
            ),
        )
        get_processor().mark_failed(document_id, code, f"Processing failed: {exc}")


@celery_app.task(
    bind=True,
    base=ProcessDocumentTask,
    name="documents.process",
    autoretry_for=(ProviderError, OperationalError),
    max_retries=_settings.task_max_retries,
    retry_backoff=_settings.task_retry_backoff_seconds,
    retry_backoff_max=_settings.task_retry_backoff_max_seconds,
    retry_jitter=True,
)
def process_document(self: Task, document_id: str) -> dict[str, object]:
    """Process an uploaded document.

    Transient failures (provider errors, lost database connections) are
    retried with exponential backoff. Permanent failures are stored on the
    document by the processor and are not retried.

    Args:
        self: Bound task (gives access to retry information).
        document_id: Document identifier as a string (JSON serializable).

    Returns:
        A small summary with the final status and counts.
    """
    with log_step(
        logger,
        "document task finished",
        document_id=document_id,
        task_id=self.request.id,
        attempt=self.request.retries + 1,
    ) as out:
        logger.info(
            "document task started",
            extra=fields(document_id=document_id, attempt=self.request.retries + 1),
        )
        outcome = get_processor().process(uuid.UUID(document_id))
        out.update(
            status=outcome.status.value,
            chunks=outcome.chunk_count,
            failed_fields=outcome.failed_fields,
        )
    return {
        "status": outcome.status.value,
        "chunks": outcome.chunk_count,
        "failed_fields": outcome.failed_fields,
    }


def enqueue_document(document_id: uuid.UUID) -> None:
    """Send the processing task for a document.

    Args:
        document_id: Document identifier.
    """
    logger.debug("sending processing task", extra=fields(document_id=str(document_id)))
    process_document.delay(str(document_id))
