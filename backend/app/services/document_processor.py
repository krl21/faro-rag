"""Processing pipeline executed by the worker for one document."""

import logging
import uuid

from opentelemetry import trace

from app.ai.extraction.field_extractor import FieldExtractor
from app.ai.extraction.field_indexing import with_filter_columns
from app.ai.extraction.prompts import pages_to_text
from app.ai.ingestion.chunker import chunk_pages
from app.ai.ingestion.embedder import embed_texts
from app.ai.ingestion.pdf_extractor import PdfExtractor, ensure_has_text
from app.ai.providers.base import EmbeddingProvider
from app.config import Settings
from app.core.errors import PermanentProcessingError
from app.core.flow_logging import fields, log_step
from app.core.telemetry import get_tracer
from app.db.repositories import (
    ChunkRepository,
    DocumentRepository,
    FieldRepository,
)
from app.db.session import session_scope
from app.domain.dtos import ChunkDraft, LLMDocument, ProcessingOutcome
from app.domain.enums import DocumentStatus, DocumentType
from app.services.storage import LocalStorage

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Extract the text, classify, and chunk, embed and extract fields for a document.

    Classification comes first: documents of type ``unknown`` stop there (no
    chunks, no embeddings, no fields) because the chat only uses policies and
    invoices.

    Every write of a run happens in short transactions: status changes are
    committed right away so the UI sees them, and chunks plus fields are
    replaced in a single final transaction. A crash in the middle leaves the
    previous chunks intact and the document in ``processing``; the retried
    task simply runs again and overwrites everything (idempotent).
    """

    def __init__(
        self,
        settings: Settings,
        storage: LocalStorage,
        extractor: PdfExtractor,
        embeddings: EmbeddingProvider,
        field_extractor: FieldExtractor,
    ) -> None:
        """Create the processor.

        Args:
            settings: Application settings.
            storage: File storage.
            extractor: PDF text extractor.
            embeddings: Embedding provider.
            field_extractor: LLM field extractor.
        """
        self._settings = settings
        self._storage = storage
        self._extractor = extractor
        self._embeddings = embeddings
        self._field_extractor = field_extractor

    def process(self, document_id: uuid.UUID) -> ProcessingOutcome:
        """Run the full pipeline.

        Args:
            document_id: Document to process.

        Returns:
            The outcome. Permanent errors (corrupt PDF, no text, too many pages)
            are stored on the document and returned as ``failed``.

        Raises:
            ProviderError: On transient provider failures, so the task retries.
        """
        span = trace.get_current_span()
        span.set_attribute("document.id", str(document_id))

        started = self._start(document_id)
        if started is None:
            logger.warning(
                "document not found, skipping", extra=fields(document_id=str(document_id))
            )
            return ProcessingOutcome(status=DocumentStatus.FAILED)

        storage_path, filename = started
        try:
            return self._run(document_id, storage_path, filename)
        except PermanentProcessingError as exc:
            logger.warning(
                "document processing failed",
                extra=fields(document_id=str(document_id), error_code=exc.code, error=exc.message),
            )
            self.mark_failed(document_id, exc.code, exc.message)
            return ProcessingOutcome(status=DocumentStatus.FAILED)

    def mark_failed(self, document_id: uuid.UUID, code: str, message: str) -> None:
        """Store a final failure on the document.

        Args:
            document_id: Document identifier.
            code: Error code.
            message: Error description.
        """
        with session_scope() as session:
            repo = DocumentRepository(session)
            document = repo.get(document_id)
            if document is not None:
                repo.set_status(
                    document, DocumentStatus.FAILED, error_code=code, error_message=message
                )
                logger.info(
                    "document marked as failed",
                    extra=fields(document_id=str(document_id), error_code=code, error=message),
                )

    def _start(self, document_id: uuid.UUID) -> tuple[str, str] | None:
        """Mark the document as processing and return where its file is.

        Args:
            document_id: Document identifier.

        Returns:
            The stored file path and the original file name, or ``None`` if
            the document does not exist.
        """
        with session_scope() as session:
            repo = DocumentRepository(session)
            document = repo.get(document_id)
            if document is None:
                return None
            repo.set_status(document, DocumentStatus.PROCESSING)
            logger.info(
                "document processing started",
                extra=fields(
                    document_id=str(document_id),
                    filename=document.filename,
                    size_bytes=document.size_bytes,
                ),
            )
            return document.storage_path, document.filename

    def _run(self, document_id: uuid.UUID, storage_path: str, filename: str) -> ProcessingOutcome:
        """Execute the pipeline steps and persist the result.

        Args:
            document_id: Document identifier.
            storage_path: Path of the stored PDF.
            filename: Original file name, sent to the LLM with the PDF.

        Returns:
            The successful outcome.
        """
        tracer = get_tracer()
        settings = self._settings

        doc_id = str(document_id)
        pdf_path = self._storage.path(storage_path)
        with (
            tracer.start_as_current_span("ingest.extract_text") as span,
            log_step(
                logger, "text extracted", document_id=doc_id, extractor=settings.pdf_extractor.value
            ) as out,
        ):
            pages = self._extractor.extract(pdf_path, max_pages=settings.max_pages)
            page_count = len(pages)
            span.set_attribute("pdf.pages", page_count)
            pages = ensure_has_text(pages)
            span.set_attribute("pdf.pages_with_text", len(pages))
            out.update(
                pages=page_count, pages_with_text=len(pages), chars=sum(len(p.text) for p in pages)
            )
            logger.debug(
                "extracted text by page",
                extra=fields(
                    document_id=doc_id, pages=[{"page": p.page, "text": p.text} for p in pages]
                ),
            )

        document = LLMDocument(
            pdf=pdf_path.read_bytes(),
            filename=filename,
            text=pages_to_text([(p.page, p.text) for p in pages]),
            page_count=page_count,
        )
        with (
            tracer.start_as_current_span("extract.classify") as span,
            log_step(
                logger,
                "document classified",
                document_id=doc_id,
                document_input=settings.llm_document_input.value,
            ) as out,
        ):
            span.set_attribute("llm.document_input", settings.llm_document_input.value)
            document_type, type_field = self._field_extractor.classify(document)
            span.set_attribute("document.type", document_type.value if document_type else "")
            out.update(
                document_type=document_type.value if document_type else None,
                confidence=type_field.confidence,
                status=type_field.status,
                attempts=type_field.attempts,
            )

        # Neither a policy nor an invoice: the chat never uses it, so no chunks,
        # no embeddings and no field extraction (saves the embedding and LLM cost).
        if document_type is DocumentType.UNKNOWN:
            logger.info(
                "document is neither a policy nor an invoice: chunks and fields skipped",
                extra=fields(document_id=doc_id),
            )
            chunks, vectors, drafts = [], [], [type_field]
        else:
            with (
                tracer.start_as_current_span("ingest.chunk") as span,
                log_step(
                    logger,
                    "text chunked",
                    document_id=doc_id,
                    chunk_size=settings.chunk_size,
                    chunk_overlap=settings.chunk_overlap,
                ) as out,
            ):
                chunks = chunk_pages(pages, settings.chunk_size, settings.chunk_overlap)
                span.set_attribute("chunks.count", len(chunks))
                out.update(chunks=len(chunks))
                logger.debug(
                    "chunks built",
                    extra=fields(
                        document_id=doc_id,
                        chunks=[
                            {"page": c.page, "index": c.chunk_index, "chars": len(c.content)}
                            for c in chunks
                        ],
                    ),
                )

            with (
                tracer.start_as_current_span("ingest.embed") as span,
                log_step(
                    logger,
                    "chunks embedded",
                    document_id=doc_id,
                    chunks=len(chunks),
                    model=self._embeddings.model,
                ) as out,
            ):
                vectors = embed_texts(
                    self._embeddings,
                    [c.content for c in chunks],
                    batch_size=settings.embedding_batch_size,
                    expected_dim=settings.embedding_dim,
                )
                span.set_attribute("chunks.count", len(vectors))
                out.update(vectors=len(vectors), dimension=settings.embedding_dim)

            # A failed classification keeps the chunks (still searchable) but has
            # no field list to extract.
            drafts = [type_field]
            if document_type is None:
                logger.warning(
                    "classification failed: chunks kept, no fields extracted",
                    extra=fields(document_id=doc_id, error=type_field.error),
                )
            else:
                with (
                    tracer.start_as_current_span("extract.fields") as span,
                    log_step(
                        logger,
                        "fields extracted",
                        document_id=doc_id,
                        document_type=document_type.value,
                    ) as out,
                ):
                    drafts += self._field_extractor.extract_fields(document_type, document)
                    span.set_attribute("fields.count", len(drafts))
                    out.update(_field_counts(drafts))
                    logger.debug(
                        "extracted fields",
                        extra=fields(
                            document_id=doc_id,
                            fields=[
                                {
                                    "name": d.name,
                                    "status": d.status,
                                    "value": d.value,
                                    "confidence": d.confidence,
                                    "page": d.page,
                                    "error": d.error,
                                }
                                for d in drafts
                            ],
                        ),
                    )
        failed = sum(1 for d in drafts if d.status == "failed")

        with (
            log_step(logger, "processing result stored", document_id=doc_id) as out,
            session_scope() as session,
        ):
            documents = DocumentRepository(session)
            stored = documents.get(document_id)
            if stored is None:  # Deleted while processing.
                logger.warning(
                    "document deleted while processing", extra=fields(document_id=doc_id)
                )
                return ProcessingOutcome(status=DocumentStatus.FAILED)
            ChunkRepository(session).replace_for_document(
                document_id,
                [
                    ChunkDraft(
                        page=c.page, chunk_index=c.chunk_index, content=c.content, embedding=v
                    )
                    for c, v in zip(chunks, vectors, strict=True)
                ],
            )
            # Each field row also stores its typed filter columns (same transaction).
            stored_fields = with_filter_columns(drafts)
            FieldRepository(session).replace_for_document(document_id, stored_fields)
            filterable = sum(1 for f in stored_fields if f.filter_columns)
            stored.page_count = page_count
            stored.document_type = document_type.value if document_type else None
            documents.set_status(stored, DocumentStatus.DONE)
            out.update(chunks=len(chunks), fields=len(drafts), filterable_fields=filterable)

        trace.get_current_span().set_attribute("chunks.count", len(chunks))
        logger.info(
            "document processed",
            extra=fields(
                document_id=doc_id,
                document_type=document_type.value if document_type else None,
                pages=page_count,
                chunks=len(chunks),
                failed_fields=failed,
            ),
        )
        return ProcessingOutcome(
            status=DocumentStatus.DONE, chunk_count=len(chunks), failed_fields=failed
        )


def _field_counts(drafts: list) -> dict[str, int]:
    """Count the extracted fields by status, for the step log.

    Args:
        drafts: Field drafts (``document_type`` included).

    Returns:
        ``fields_ok``, ``fields_not_found`` and ``fields_failed``.
    """
    return {
        f"fields_{status}": sum(1 for d in drafts if d.status == status)
        for status in ("ok", "not_found", "failed")
    }
