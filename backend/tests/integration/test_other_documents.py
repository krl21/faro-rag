"""Documents classified as "other": no chunks, no fields, out of the chat."""

import pytest
from sqlalchemy import text

from app.db.session import engine
from tests.fixtures.pdf_factory import INVOICE_TEXT, POLICY_TEXT, make_pdf

pytestmark = pytest.mark.integration

OTHER_TEXT = "Acta de la reunión anual\nAsistentes: Dirección y Recursos Humanos\nOrden del día"


def _upload(client, text_: str, filename: str) -> str:
    response = client.post(
        "/documents", files={"file": (filename, make_pdf([text_]), "application/pdf")}
    )
    return response.json()["id"]


def test_other_document_is_done_without_chunks_or_fields(client):
    doc_id = _upload(client, OTHER_TEXT, "acta.pdf")
    detail = client.get(f"/documents/{doc_id}").json()
    assert detail["status"] == "done"
    assert detail["document_type"] == "other"
    assert detail["chunk_count"] == 0
    assert [f["name"] for f in detail["fields"]] == ["document_type"]
    assert detail["fields"][0]["editable"] is False


def test_other_document_is_still_listed_in_the_documents_list(client):
    doc_id = _upload(client, OTHER_TEXT, "acta.pdf")
    listed = {d["id"]: d["document_type"] for d in client.get("/documents").json()}
    assert listed[doc_id] == "other"


def test_other_document_cannot_be_asked_about(client):
    doc_id = _upload(client, OTHER_TEXT, "acta.pdf")
    response = client.post(f"/documents/{doc_id}/ask", json={"question": "¿qué dice el acta?"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "document_not_queryable"


def test_other_document_is_left_out_of_chat_listings(client):
    _upload(client, OTHER_TEXT, "acta.pdf")
    policy_id = _upload(client, POLICY_TEXT, "poliza.pdf")
    invoice_id = _upload(client, INVOICE_TEXT, "factura.pdf")
    body = client.post("/ask", json={"question": "documentos subidos hoy"}).json()
    assert {d["id"] for d in body["documents"]} == {policy_id, invoice_id}


def test_other_document_never_answers_chat_questions(client):
    doc_id = _upload(client, OTHER_TEXT, "acta.pdf")
    body = client.post(
        "/ask", json={"question": "¿qué asistentes hubo en la reunión anual?"}
    ).json()
    assert body["answered"] is False
    assert all(c["document_id"] != doc_id for c in body["citations"])


def test_old_chunks_of_other_documents_are_ignored_by_search(client):
    # A document processed before this rule may still have chunks.
    doc_id = _upload(client, POLICY_TEXT, "poliza.pdf")
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE documents SET document_type = 'other' WHERE id = :id"), {"id": doc_id}
        )
    body = client.post("/ask", json={"question": "número de póliza FS-2024-001 coberturas"}).json()
    assert all(c["document_id"] != doc_id for c in body["citations"])


def test_fields_of_other_documents_are_not_editable(client):
    doc_id = _upload(client, OTHER_TEXT, "acta.pdf")
    response = client.patch(f"/documents/{doc_id}/fields/holder", json={"value": "Ana"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "field_not_found"
