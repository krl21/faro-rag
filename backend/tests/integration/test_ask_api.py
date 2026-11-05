import pytest

from app.ai.rag.answerer import NOT_ENOUGH_INFORMATION
from tests.fixtures.pdf_factory import INVOICE_TEXT, POLICY_TEXT, make_pdf

pytestmark = pytest.mark.integration


def _upload(client, text: str, filename: str) -> str:
    response = client.post(
        "/documents", files={"file": (filename, make_pdf([text]), "application/pdf")}
    )
    return response.json()["id"]


def test_answer_cites_document_and_page(client):
    doc_id = _upload(client, POLICY_TEXT, "poliza.pdf")
    response = client.post("/ask", json={"question": "número de póliza"})
    assert response.status_code == 200
    body = response.json()
    assert body["answered"] is True
    assert "[1]" in body["answer"]
    citation = body["citations"][0]
    assert citation["marker"] == 1
    assert citation["document_id"] == doc_id
    assert citation["filename"] == "poliza.pdf"
    assert citation["page"] == 1


def test_no_evidence_returns_not_enough_information(client):
    _upload(client, POLICY_TEXT, "poliza.pdf")
    body = client.post("/ask", json={"question": "receta de paella con mariscos"}).json()
    assert body["answer"] == NOT_ENOUGH_INFORMATION
    assert body["answered"] is False
    assert body["citations"] == []
    assert body["mode"] == "answer"


def test_document_filter_restricts_the_sources(client):
    _upload(client, POLICY_TEXT, "poliza.pdf")
    invoice_id = _upload(client, INVOICE_TEXT, "factura.pdf")
    body = client.post(
        "/ask", json={"question": "importe de la póliza FS-2024-001", "document_id": invoice_id}
    ).json()
    assert body["answered"] is True
    assert {c["document_id"] for c in body["citations"]} == {invoice_id}


def test_question_is_validated(client):
    assert client.post("/ask", json={"question": ""}).status_code == 422
