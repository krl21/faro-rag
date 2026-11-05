"""POST /documents/{id}/ask: questions about one document, optionally by pages."""

import pytest

from tests.fixtures.pdf_factory import INVOICE_TEXT, POLICY_TEXT, make_pdf

pytestmark = pytest.mark.integration


def _upload(client, *pages: str, filename: str = "doc.pdf") -> str:
    response = client.post(
        "/documents", files={"file": (filename, make_pdf(list(pages)), "application/pdf")}
    )
    return response.json()["id"]


def _ask(client, doc_id: str, **body):
    return client.post(f"/documents/{doc_id}/ask", json=body)


def test_answer_cites_only_that_document(client):
    policy_id = _upload(client, POLICY_TEXT, filename="poliza.pdf")
    _upload(client, INVOICE_TEXT, filename="factura.pdf")
    response = _ask(client, policy_id, question="número de póliza")
    assert response.status_code == 200
    body = response.json()
    assert body["answered"] is True
    assert body["mode"] == "answer"
    assert body["filter_source"] == "document"
    assert body["filters"]["include"] == []
    assert {c["document_id"] for c in body["citations"]} == {policy_id}


def test_pages_restrict_the_fragments_and_the_fields(client):
    doc_id = _upload(
        client, "Portada sin datos", POLICY_TEXT, "Anexo: el deducible es de 150 euros"
    )
    body = _ask(client, doc_id, question="¿cuál es el deducible?", pages={"from": 3}).json()
    assert body["answered"] is True
    assert {c["page"] for c in body["citations"]} == {3}  # The policy fields are on page 2.
    body = _ask(client, doc_id, question="¿cuál es el deducible?", pages={"to": 2}).json()
    assert all(c["page"] is not None and c["page"] <= 2 for c in body["citations"])
    assert "150" not in body["answer"]


def test_no_filter_interpretation_and_no_llm_for_filters(client, monkeypatch):
    from app.ai.query import interpreter

    def fail(*args, **kwargs):
        raise AssertionError("filters must not be interpreted")

    monkeypatch.setattr(interpreter.QueryInterpreter, "interpret", fail)
    doc_id = _upload(client, INVOICE_TEXT)
    assert _ask(client, doc_id, question="facturas de ayer de más de 1000 €").status_code == 200


def test_conversation_is_created_and_continued(client):
    doc_id = _upload(client, POLICY_TEXT)
    first = _ask(client, doc_id, question="número de póliza").json()
    second = _ask(
        client, doc_id, question="¿y la vigencia?", conversation_id=first["conversation_id"]
    ).json()
    assert second["conversation_id"] == first["conversation_id"]
    messages = client.get(f"/conversations/{first['conversation_id']}").json()["messages"]
    assert len(messages) == 4
    assert messages[1]["details"]["document_id"] == doc_id
    assert messages[1]["details"]["filter_source"] == "document"


def test_pages_are_stored_in_the_conversation(client):
    doc_id = _upload(client, POLICY_TEXT)
    body = _ask(client, doc_id, question="número de póliza", pages={"to": 1}).json()
    messages = client.get(f"/conversations/{body['conversation_id']}").json()["messages"]
    assert messages[1]["details"]["pages"] == {"from": None, "to": 1}


def test_unknown_document_returns_404(client):
    response = _ask(client, "00000000-0000-0000-0000-000000000000", question="hola mundo")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "document_not_found"


def test_document_not_processed_returns_409(client):
    doc_id = _upload(client, "", "")
    response = _ask(client, doc_id, question="número de póliza")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "document_not_ready"


def test_unknown_conversation_returns_404(client):
    doc_id = _upload(client, POLICY_TEXT)
    response = _ask(
        client,
        doc_id,
        question="hola mundo",
        conversation_id="00000000-0000-0000-0000-000000000001",
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "conversation_not_found"


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"question": "ab"},
        {"question": "hola mundo", "pages": {"from": 4, "to": 2}},
        {"question": "hola mundo", "pages": {"from": 0}},
        {"question": "hola mundo", "conversation_id": "x"},
    ],
)
def test_invalid_bodies_return_422(client, body):
    doc_id = _upload(client, POLICY_TEXT)
    assert _ask(client, doc_id, **body).status_code == 422


def test_invalid_document_id_returns_422(client):
    assert client.post("/documents/no-uuid/ask", json={"question": "hola mundo"}).status_code == 422


def test_shares_the_rate_limit(client, settings, monkeypatch):
    doc_id = _upload(client, POLICY_TEXT)
    monkeypatch.setattr(settings, "ask_rate_limit", "2/minute")
    codes = [_ask(client, doc_id, question="número de póliza").status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_question_about_an_extracted_field_is_answered_from_it(client, monkeypatch):
    from app.ai.rag import retriever

    doc_id = _upload(client, INVOICE_TEXT, filename="factura.pdf")
    # No text fragment passes retrieval (like a "check this value" question).
    monkeypatch.setattr(retriever.HybridRetriever, "retrieve", lambda self, *a, **k: [])
    body = _ask(
        client, doc_id, question="necesito que me corrijas si la fecha de la factura es del 2003"
    ).json()
    assert body["answered"] is True
    fields_cited = {c["field"] for c in body["citations"] if c["source"] == "field"}
    assert fields_cited
    assert all(c["document_id"] == doc_id for c in body["citations"])


def test_fields_are_not_used_by_the_general_chat(client, monkeypatch):
    from app.ai.rag import retriever

    _upload(client, INVOICE_TEXT, filename="factura.pdf")
    monkeypatch.setattr(retriever.HybridRetriever, "retrieve", lambda self, *a, **k: [])
    body = client.post("/ask", json={"question": "¿qué cubre la asistencia?"}).json()
    assert body["answered"] is False
