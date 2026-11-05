"""Failure handling: provider errors, final task failure, enqueue failure and startup checks."""

import hashlib
import json
import uuid

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from app.ai.extraction.field_extractor import FieldExtractor
from app.ai.providers.fake_provider import FakeEmbeddingProvider, FakeLLMProvider
from app.config import get_settings
from app.core.errors import ProviderError, QueueUnavailableError
from app.core.startup_checks import check_embedding_dimension
from app.db.models import Document
from app.db.repositories import DocumentRepository
from app.db.session import SessionLocal, engine, session_scope
from app.domain.enums import DocumentStatus
from app.services import document_service
from app.services.document_processor import DocumentProcessor
from app.services.document_service import DocumentService
from app.services.storage import LocalStorage
from app.worker.tasks import process_document
from tests.fixtures.pdf_factory import POLICY_TEXT, make_pdf
from tests.fixtures.text_layer_extractor import TextLayerExtractor

pytestmark = pytest.mark.integration


class _FailingEmbeddings(FakeEmbeddingProvider):
    def embed(self, texts):
        raise ProviderError("embedding service down")


def _create_pending(content: bytes) -> uuid.UUID:
    content_hash = hashlib.sha256(content).hexdigest()
    path = LocalStorage(get_settings().storage_dir).save(content_hash, content)
    with session_scope() as session:
        document = Document(
            filename="p.pdf",
            content_hash=content_hash,
            size_bytes=len(content),
            storage_path=path,
            status=DocumentStatus.PENDING,
        )
        session.add(document)
        session.flush()
        return document.id


def _processor(embeddings=None, llm=None) -> DocumentProcessor:
    settings = get_settings()
    return DocumentProcessor(
        settings=settings,
        storage=LocalStorage(settings.storage_dir),
        extractor=TextLayerExtractor(),
        embeddings=embeddings or FakeEmbeddingProvider(settings.embedding_dim),
        field_extractor=FieldExtractor(
            llm or FakeLLMProvider(),
            retry_delays=[0, 0],
            classification_max_chars=5000,
            sleep=lambda _: None,
        ),
    )


def _document(document_id: uuid.UUID) -> Document:
    with session_scope() as session:
        return DocumentRepository(session).get(document_id, with_fields=True)


def test_provider_error_propagates_so_celery_retries(clean_database):
    document_id = _create_pending(make_pdf([POLICY_TEXT]))
    with pytest.raises(ProviderError):
        _processor(embeddings=_FailingEmbeddings(get_settings().embedding_dim)).process(document_id)
    assert _document(document_id).status == DocumentStatus.PROCESSING


def test_final_task_failure_marks_document_failed(clean_database):
    document_id = _create_pending(make_pdf([POLICY_TEXT]))
    process_document.on_failure(
        ProviderError("embedding service down"), "task-1", (str(document_id),), {}, None
    )
    document = _document(document_id)
    assert document.status == DocumentStatus.FAILED
    assert document.error_code == "provider_error"
    assert "embedding service down" in document.error_message


def test_invalid_llm_output_keeps_document_done_with_failed_fields(clean_database):
    document_id = _create_pending(make_pdf([POLICY_TEXT]))
    llm = FakeLLMProvider(
        scripted={
            "classify": [json.dumps({"tipo": "poliza", "confianza": "alta"})],
            "extract.policy": ["no es json"] * 3,
        }
    )
    outcome = _processor(llm=llm).process(document_id)
    document = _document(document_id)
    assert outcome.status == DocumentStatus.DONE
    assert document.status == DocumentStatus.DONE
    failed = {f.label for f in document.fields if f.status == "failed"}
    assert failed == {
        "policy_number",
        "validity",
        "coverages",
        "holder",
        "tax_id",
        "license_plate",
    }
    assert all(f.attempts == 3 for f in document.fields if f.status == "failed")


def test_reprocessing_replaces_fields_without_duplicates(clean_database):
    document_id = _create_pending(make_pdf([POLICY_TEXT]))
    _processor().process(document_id)
    _processor().process(document_id)
    names = [f.label for f in _document(document_id).fields]
    assert len(names) == len(set(names))


def _broken_enqueue(_: uuid.UUID) -> None:
    raise ConnectionError("redis down")


def _upload_with(enqueue, content: bytes):
    session = SessionLocal()
    try:
        service = DocumentService(session, LocalStorage(get_settings().storage_dir), enqueue)
        return service.upload("p.pdf", content)
    finally:
        session.close()


def test_enqueue_failure_marks_document_failed_and_logs_an_error(clean_database, caplog):
    with pytest.raises(QueueUnavailableError):
        _upload_with(_broken_enqueue, make_pdf([POLICY_TEXT]))
    with session_scope() as session:
        document = DocumentRepository(session).list()[0]
        assert document.status == DocumentStatus.FAILED
        assert document.error_code == "queue_unavailable"
    errors = [r for r in caplog.records if r.levelname == "ERROR"]
    assert any("processing queue unavailable" in r.getMessage() for r in errors)
    assert any(getattr(r, "error", "") == "redis down" for r in errors)


def _in_memory_tracer(monkeypatch) -> InMemorySpanExporter:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(document_service, "get_tracer", lambda: provider.get_tracer("test"))
    return exporter


def test_enqueue_failure_is_recorded_on_its_own_span(clean_database, monkeypatch):
    exporter = _in_memory_tracer(monkeypatch)
    with pytest.raises(QueueUnavailableError):
        _upload_with(_broken_enqueue, make_pdf([POLICY_TEXT]))
    (span,) = exporter.get_finished_spans()
    assert span.name == "queue.enqueue"
    assert span.status.status_code is StatusCode.ERROR
    assert span.status.description == "processing queue unavailable"
    (event,) = span.events
    assert event.name == "exception"
    assert event.attributes["exception.message"] == "redis down"


def test_successful_enqueue_span_is_ok(clean_database, monkeypatch):
    exporter = _in_memory_tracer(monkeypatch)
    result = _upload_with(lambda _: None, make_pdf([POLICY_TEXT]))
    (span,) = exporter.get_finished_spans()
    assert span.name == "queue.enqueue"
    assert span.status.status_code is StatusCode.UNSET
    assert span.attributes["document.id"] == str(result.document.id)


def test_uploading_again_after_queue_recovers_processes_the_document(clean_database):
    content = make_pdf([POLICY_TEXT])
    with pytest.raises(QueueUnavailableError):
        _upload_with(_broken_enqueue, content)
    sent: list[uuid.UUID] = []
    result = _upload_with(sent.append, content)
    assert result.duplicate is True
    assert result.requeued is True
    assert sent == [result.document.id]
    document = _document(result.document.id)
    assert document.status == DocumentStatus.PENDING
    assert document.error_code is None


def test_uploading_again_while_queue_is_still_down_fails_again(clean_database):
    content = make_pdf([POLICY_TEXT])
    with pytest.raises(QueueUnavailableError):
        _upload_with(_broken_enqueue, content)
    with pytest.raises(QueueUnavailableError):
        _upload_with(_broken_enqueue, content)
    with session_scope() as session:
        documents = DocumentRepository(session).list()
        assert len(documents) == 1
        assert documents[0].status == DocumentStatus.FAILED


@pytest.mark.parametrize("status", [DocumentStatus.PENDING, DocumentStatus.PROCESSING])
def test_duplicates_in_progress_are_not_requeued(clean_database, status):
    content = make_pdf([POLICY_TEXT])
    document_id = _create_pending(content)
    with session_scope() as session:
        DocumentRepository(session).get(document_id).status = status
    sent: list[uuid.UUID] = []
    result = _upload_with(sent.append, content)
    assert (result.duplicate, result.requeued) == (True, False)
    assert sent == []


def test_startup_check_passes_when_dimensions_match(migrated_database):
    provider = FakeEmbeddingProvider(get_settings().embedding_dim)
    assert check_embedding_dimension(get_settings(), provider, engine) is True


def test_startup_check_fails_on_dimension_mismatch(migrated_database, caplog):
    provider = FakeEmbeddingProvider(get_settings().embedding_dim + 1)
    assert check_embedding_dimension(get_settings(), provider, engine) is False
    assert "embedding dimension mismatch" in caplog.text
