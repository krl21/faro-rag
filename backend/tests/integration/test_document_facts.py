"""Free label-value data: stored when a document is processed and used by the chat."""

import uuid

import pytest
from sqlalchemy import select

from app.db.models import ExtractedField
from app.db.session import session_scope
from tests.fixtures.pdf_factory import INVOICE_TEXT, make_pdf

pytestmark = pytest.mark.integration

EXTRA_PAGE = """Datos del pago
Forma de pago: Transferencia a 30 días
Entidad: Banco del Faro
Base imponible
1.033,47 EUR"""


def _upload(client, *pages: str) -> str:
    response = client.post(
        "/documents", files={"file": ("factura.pdf", make_pdf(list(pages)), "application/pdf")}
    )
    return response.json()["id"]


def _free_data(doc_id: str) -> list[ExtractedField]:
    with session_scope() as session:
        rows = session.scalars(
            select(ExtractedField).where(
                ExtractedField.document_id == uuid.UUID(doc_id),
                ExtractedField.is_predefined.is_(False),
            )
        ).all()
        session.expunge_all()
        return list(rows)


def test_free_data_are_stored_with_page_and_embedding(client):
    doc_id = _upload(client, INVOICE_TEXT, EXTRA_PAGE)
    data = {(row.page, row.label): row for row in _free_data(doc_id)}
    assert data[(2, "Forma de pago")].value == "Transferencia a 30 días"
    assert data[(2, "Base imponible")].value == "1.033,47 EUR"
    assert data[(1, "Importe total")].value == "1.250,50 EUR"
    assert all(row.embedding is not None and row.status == "ok" for row in data.values())


def test_free_data_are_not_listed_as_known_fields(client):
    doc_id = _upload(client, INVOICE_TEXT, EXTRA_PAGE)
    names = [f["name"] for f in client.get(f"/documents/{doc_id}").json()["fields"]]
    assert None not in names
    assert "invoice_amount" in names


def test_unknown_documents_store_no_free_data(client):
    doc_id = _upload(client, "Acta de reunión\nAsistentes: Ana y Luis\nLugar: Sala 3")
    assert _free_data(doc_id) == []


def test_document_question_receives_the_relevant_free_data(client, monkeypatch):
    from app.ai.rag import answerer

    received = []
    original = answerer.build_answer_messages

    def spy(question, fragments, facts=()):
        received.extend(facts)
        return original(question, fragments, facts)

    monkeypatch.setattr(answerer, "build_answer_messages", spy)
    doc_id = _upload(client, INVOICE_TEXT, EXTRA_PAGE)
    body = client.post(f"/documents/{doc_id}/ask", json={"question": "¿forma de pago?"}).json()
    assert body["answered"] is True
    free = [f for f in received if f.name is None]
    assert any(f.label == "Forma de pago" and f.page == 2 for f in free)


def test_number_of_free_data_is_limited(client, monkeypatch, settings):
    from app.ai.rag import answerer

    monkeypatch.setattr(settings, "retrieval_facts_top_k", 2)
    received = []
    original = answerer.build_answer_messages

    def spy(question, fragments, facts=()):
        received.extend(facts)
        return original(question, fragments, facts)

    monkeypatch.setattr(answerer, "build_answer_messages", spy)
    doc_id = _upload(client, INVOICE_TEXT, EXTRA_PAGE)
    client.post(f"/documents/{doc_id}/ask", json={"question": "importe y forma de pago"})
    assert len([f for f in received if f.name is None]) == 2


def test_page_range_limits_the_free_data(client, monkeypatch):
    from app.ai.rag import answerer

    received = []
    original = answerer.build_answer_messages

    def spy(question, fragments, facts=()):
        received.extend(facts)
        return original(question, fragments, facts)

    monkeypatch.setattr(answerer, "build_answer_messages", spy)
    doc_id = _upload(client, INVOICE_TEXT, EXTRA_PAGE)
    client.post(f"/documents/{doc_id}/ask", json={"question": "forma de pago", "pages": {"to": 1}})
    assert all(f.page == 1 for f in received if f.name is None)


def test_general_chat_free_data_compete_with_the_chunks(client, monkeypatch):
    from app.ai.rag import answerer

    received = []
    original = answerer.build_answer_messages

    def spy(question, fragments, facts=()):
        received.append((list(fragments), list(facts)))
        return original(question, fragments, facts)

    monkeypatch.setattr(answerer, "build_answer_messages", spy)
    _upload(client, INVOICE_TEXT, EXTRA_PAGE)
    body = client.post("/ask", json={"question": "Banco del Faro"}).json()
    assert body["answered"] is True
    fragments, facts = received[-1]
    assert any(f.label == "Entidad" and f.value == "Banco del Faro" for f in facts)
    # One ranking, one budget: chunks and data together never exceed RETRIEVAL_TOP_K.
    from app.config import get_settings

    assert len(fragments) + len(facts) <= get_settings().retrieval_top_k
