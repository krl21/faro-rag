import hashlib
import uuid

import pytest

from app.config import get_settings
from app.db.models import Document
from app.db.repositories import ChunkRepository
from app.db.session import session_scope
from app.domain.enums import DocumentStatus
from app.services.storage import LocalStorage
from app.worker.tasks import get_processor, process_document
from tests.fixtures.pdf_factory import POLICY_TEXT, make_pdf

pytestmark = pytest.mark.integration


@pytest.fixture
def pending_document(clean_database) -> uuid.UUID:
    content = make_pdf([POLICY_TEXT, "Condiciones generales de la póliza. " * 60])
    content_hash = hashlib.sha256(content).hexdigest()
    path = LocalStorage(get_settings().storage_dir).save(content_hash, content)
    with session_scope() as session:
        document = Document(
            filename="poliza.pdf",
            content_hash=content_hash,
            size_bytes=len(content),
            storage_path=path,
            status=DocumentStatus.PENDING,
        )
        session.add(document)
        session.flush()
        return document.id


def _chunk_count(document_id: uuid.UUID) -> int:
    with session_scope() as session:
        return ChunkRepository(session).count_for_document(document_id)


def test_task_processes_document_through_celery(pending_document, eager_celery):
    result = process_document.delay(str(pending_document)).get()
    assert result["status"] == "done"
    assert result["chunks"] == _chunk_count(pending_document) > 1


def test_reprocessing_does_not_duplicate_chunks(pending_document):
    first = get_processor().process(pending_document)
    second = get_processor().process(pending_document)
    assert first.chunk_count == second.chunk_count
    assert _chunk_count(pending_document) == first.chunk_count


def test_missing_document_is_skipped(clean_database):
    outcome = get_processor().process(uuid.uuid4())
    assert outcome.status is DocumentStatus.FAILED
