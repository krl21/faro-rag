"""Document lifecycle used by the API: upload, deduplication and queries."""

import hashlib
import logging
import uuid
from collections.abc import Callable

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import DocumentNotFoundError, QueueUnavailableError
from app.core.flow_logging import fields
from app.core.telemetry import get_tracer
from app.db.models import Document
from app.db.repositories import ChunkRepository, DocumentRepository
from app.domain.dtos import UploadResult
from app.domain.enums import DocumentStatus
from app.services.storage import LocalStorage

logger = logging.getLogger(__name__)

DUPLICATE_MESSAGE = "A document with the same content already exists (id {id})"
REQUEUED_MESSAGE = "A document with the same content had failed (id {id}); it has been queued again"
QUEUE_ERROR_MESSAGE = "The processing task could not be enqueued"


class DocumentService:
    """Create documents and read their state."""

    def __init__(
        self,
        session: Session,
        storage: LocalStorage,
        enqueue: Callable[[uuid.UUID], None],
    ) -> None:
        """Create the service.

        Args:
            session: Active SQLAlchemy session.
            storage: File storage.
            enqueue: Sends the processing task for a document id.
        """
        self._session = session
        self._documents = DocumentRepository(session)
        self._chunks = ChunkRepository(session)
        self._storage = storage
        self._enqueue = enqueue

    def upload(self, filename: str, content: bytes) -> UploadResult:
        """Store a validated PDF and enqueue its processing.

        Files are deduplicated by SHA-256: uploading the same content again
        returns the existing document and logs a warning. If that document had
        ``failed`` (for example because the queue was down), it is reset to
        ``pending`` and enqueued again, so uploading it again is the way to
        retry. The task is enqueued only after the row is committed, so the
        worker always finds it.

        Args:
            filename: Safe filename.
            content: PDF bytes.

        Returns:
            The document, whether it was a duplicate and whether it was requeued.

        Raises:
            QueueUnavailableError: If the task cannot be sent to the broker. The
                document is then marked ``failed`` so it never stays ``pending``.
        """
        content_hash = hashlib.sha256(content).hexdigest()
        logger.debug(
            "upload hashed", extra=fields(content_hash=content_hash, size_bytes=len(content))
        )
        existing = self._documents.get_by_hash(content_hash)
        if existing is not None:
            return self._handle_duplicate(existing, filename)

        path = self._storage.save(content_hash, content)
        logger.debug("upload stored", extra=fields(storage_path=path))
        document = Document(
            filename=filename,
            content_hash=content_hash,
            size_bytes=len(content),
            storage_path=path,
            status=DocumentStatus.PENDING,
        )
        try:
            self._documents.add(document)
            self._session.commit()
        except IntegrityError:
            # A concurrent upload of the same file won the race.
            self._session.rollback()
            existing = self._documents.get_by_hash(content_hash)
            if existing is None:
                raise
            return self._handle_duplicate(existing, filename)

        trace.get_current_span().set_attribute("document.id", str(document.id))
        logger.info(
            "document created",
            extra=fields(
                document_id=str(document.id),
                filename=filename,
                size_bytes=len(content),
                content_hash=content_hash,
                status=document.status,
            ),
        )
        self._enqueue_or_fail(document)
        return UploadResult(document=document, duplicate=False)

    def list(self, limit: int, offset: int) -> list[Document]:
        """List documents, newest first.

        Args:
            limit: Page size.
            offset: Rows to skip.

        Returns:
            The documents.
        """
        documents = self._documents.list(limit=limit, offset=offset)
        logger.debug(
            "documents listed", extra=fields(limit=limit, offset=offset, returned=len(documents))
        )
        return documents

    def get(self, document_id: uuid.UUID) -> tuple[Document, int]:
        """Fetch a document with its fields and chunk count.

        Args:
            document_id: Document identifier.

        Returns:
            The document and its number of chunks.

        Raises:
            DocumentNotFoundError: If the document does not exist.
        """
        document = self._documents.get(document_id, with_fields=True)
        if document is None:
            logger.info("document not found", extra=fields(document_id=str(document_id)))
            raise DocumentNotFoundError(f"Document {document_id} not found")
        chunk_count = self._chunks.count_for_document(document_id)
        logger.debug(
            "document read",
            extra=fields(
                document_id=str(document_id),
                status=document.status,
                document_type=document.document_type,
                fields=len(document.fields),
                chunks=chunk_count,
            ),
        )
        return document, chunk_count

    def _enqueue_or_fail(self, document: Document) -> None:
        """Send the processing task, or mark the document failed if the queue is down.

        The call runs inside its own ``queue.enqueue`` span. A broker failure
        is logged at ``ERROR`` and recorded on that span, so it shows up in the
        logs and in Jaeger within the request trace. The own span matters: when
        publishing fails, Celery's instrumentation never ends its publish span,
        so an error recorded there would never be exported.

        Args:
            document: Committed document to process.

        Raises:
            QueueUnavailableError: If the task cannot be sent to the broker. The
                document is then marked ``failed`` so it never stays ``pending``.
        """
        try:
            with get_tracer().start_as_current_span(
                "queue.enqueue", record_exception=False, set_status_on_exception=False
            ) as span:
                span.set_attribute("document.id", str(document.id))
                try:
                    self._enqueue(document.id)
                except Exception as exc:
                    span.record_exception(exc)
                    span.set_status(Status(StatusCode.ERROR, "processing queue unavailable"))
                    raise
        except Exception as exc:
            logger.error(
                "processing queue unavailable: document marked as failed",
                extra={"document_id": str(document.id), "error": str(exc)},
            )
            self._documents.set_status(
                document,
                DocumentStatus.FAILED,
                error_code=QueueUnavailableError.code,
                error_message=QUEUE_ERROR_MESSAGE,
            )
            self._session.commit()
            raise QueueUnavailableError("The processing queue is unavailable") from exc
        logger.info("document enqueued", extra={"document_id": str(document.id)})

    def _handle_duplicate(self, existing: Document, filename: str) -> UploadResult:
        """Return a duplicate upload, enqueuing it again if it had failed.

        Args:
            existing: Document with the same content.
            filename: Filename of the new upload.

        Returns:
            The duplicate result.

        Raises:
            QueueUnavailableError: If a failed document cannot be enqueued again.
        """
        self._log_duplicate(existing, filename)
        if existing.status != DocumentStatus.FAILED:
            return UploadResult(document=existing, duplicate=True)
        logger.info(
            "failed document uploaded again: retrying its processing",
            extra={"document_id": str(existing.id), "previous_error": existing.error_code},
        )
        trace.get_current_span().set_attribute("document.requeued", True)
        self._documents.set_status(existing, DocumentStatus.PENDING)
        self._session.commit()
        self._enqueue_or_fail(existing)
        return UploadResult(document=existing, duplicate=True, requeued=True)

    @staticmethod
    def _log_duplicate(existing: Document, filename: str) -> None:
        """Log the duplicate alert and tag the current span.

        Args:
            existing: Document with the same content.
            filename: Filename of the new upload.
        """
        logger.warning(
            "duplicate document upload",
            extra={
                "document_id": str(existing.id),
                "existing_filename": existing.filename,
                "uploaded_filename": filename,
            },
        )
        span = trace.get_current_span()
        span.set_attribute("document.id", str(existing.id))
        span.set_attribute("document.duplicate", True)
