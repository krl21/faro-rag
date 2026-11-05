"""End-to-end processing with the document sent to the LLM as PDF or as text."""

import hashlib
import uuid

import pytest

from app.ai.extraction.field_extractor import FieldExtractor
from app.ai.providers.fake_provider import FakeEmbeddingProvider, FakeLLMProvider
from app.config import get_settings
from app.db.models import Document
from app.db.repositories import DocumentRepository
from app.db.session import session_scope
from app.domain.enums import DocumentInput, DocumentStatus, DocumentType
from app.services.document_processor import DocumentProcessor
from app.services.storage import LocalStorage
from tests.fixtures.pdf_factory import make_pdf
from tests.fixtures.text_layer_extractor import TextLayerExtractor

pytestmark = pytest.mark.integration

COVER = "Condiciones generales del contrato. " * 400
INVOICE_PAGE = "Factura número 7\nReferencia póliza: FS-1001\nImporte total: 1.250,50 EUR"


def _pending(content: bytes) -> uuid.UUID:
    content_hash = hashlib.sha256(content).hexdigest()
    path = LocalStorage(get_settings().storage_dir).save(content_hash, content)
    with session_scope() as session:
        document = Document(
            filename="largo.pdf",
            content_hash=content_hash,
            size_bytes=len(content),
            storage_path=path,
            status=DocumentStatus.PENDING,
        )
        session.add(document)
        session.flush()
        return document.id


def _process(document_id: uuid.UUID, mode: DocumentInput, llm: FakeLLMProvider) -> Document:
    settings = get_settings().model_copy(update={"llm_document_input": mode})
    DocumentProcessor(
        settings=settings,
        storage=LocalStorage(settings.storage_dir),
        extractor=TextLayerExtractor(),
        embeddings=FakeEmbeddingProvider(settings.embedding_dim),
        field_extractor=FieldExtractor(
            llm,
            retry_delays=[],
            classification_max_chars=200,
            document_input=mode,
            sleep=lambda _: None,
        ),
    ).process(document_id)
    with session_scope() as session:
        return DocumentRepository(session).get(document_id, with_fields=True)


def test_pdf_mode_classifies_with_every_page(clean_database):
    # The invoice data is on page 3, after two long cover pages.
    document_id = _pending(make_pdf([COVER, COVER, INVOICE_PAGE]))
    llm = FakeLLMProvider()
    document = _process(document_id, DocumentInput.PDF, llm)
    assert document.status == DocumentStatus.DONE
    assert document.document_type == DocumentType.INVOICE
    amount = next(f for f in document.fields if f.label == "invoice_amount")
    assert amount.value == {"amount": "1250.50", "currency": "EUR"}
    assert all(messages[-1].attachments for _, messages in llm.calls)


def test_text_mode_classifies_with_the_start_only(clean_database):
    # Same document as text: classification only sees the first 200 characters.
    document_id = _pending(make_pdf([COVER, COVER, INVOICE_PAGE]))
    llm = FakeLLMProvider()
    document = _process(document_id, DocumentInput.TEXT, llm)
    assert document.document_type == DocumentType.UNKNOWN
    assert all(not messages[-1].attachments for _, messages in llm.calls)
    assert [purpose for purpose, _ in llm.calls] == ["classify"]  # "unknown": no extraction.


def test_text_mode_extraction_gets_every_page(clean_database):
    document_id = _pending(
        make_pdf([INVOICE_PAGE, COVER, "Anexo final con las condiciones particulares del taller"])
    )
    llm = FakeLLMProvider()
    _process(document_id, DocumentInput.TEXT, llm)
    extract_prompt = llm.calls[1][1][-1].content
    assert "[Página 3]" in extract_prompt


def test_text_mode_extracts_from_every_page(clean_database):
    document_id = _pending(make_pdf([INVOICE_PAGE, "Anexo: matrícula 1234-BCD"]))
    document = _process(document_id, DocumentInput.TEXT, FakeLLMProvider())
    plate = next(f for f in document.fields if f.label == "license_plate")
    assert document.document_type == DocumentType.INVOICE
    assert plate.value == "1234-BCD"
