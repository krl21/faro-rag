"""PATCH /documents/{id}/fields/{name}: user edits, validation and reindexing."""

import pytest

from tests.fixtures.pdf_factory import INVOICE_TEXT, POLICY_TEXT, make_pdf

pytestmark = pytest.mark.integration


def _upload(client, *pages: str, filename: str = "doc.pdf") -> str:
    response = client.post(
        "/documents", files={"file": (filename, make_pdf(list(pages)), "application/pdf")}
    )
    return response.json()["id"]


def _fields(client, doc_id: str) -> dict:
    return {f["name"]: f for f in client.get(f"/documents/{doc_id}").json()["fields"]}


def _patch(client, doc_id: str, name: str, value):
    return client.patch(f"/documents/{doc_id}/fields/{name}", json={"value": value})


def test_detail_exposes_page_value_type_and_editable(client):
    doc_id = _upload(client, "Portada del contrato", POLICY_TEXT)
    fields = _fields(client, doc_id)
    assert fields["policy_number"]["page"] == 2
    assert fields["policy_number"]["value_type"] == "text"
    assert fields["validity"]["value_type"] == "period"
    assert fields["coverages"]["value_type"] == "text_list"
    assert fields["policy_number"]["editable"] is True
    assert fields["document_type"]["editable"] is False
    assert fields["policy_number"]["original_value"] is None
    assert fields["policy_number"]["edited_at"] is None


def test_edit_keeps_the_original_and_marks_the_field_edited(client):
    doc_id = _upload(client, POLICY_TEXT)
    response = _patch(client, doc_id, "policy_number", "FS-9999")
    assert response.status_code == 200
    body = response.json()
    assert body["value"] == "FS-9999"
    assert body["status"] == "edited"
    assert body["original_value"] == "FS-2024-001"
    assert body["confidence"] is None
    assert body["edited_at"] is not None
    assert _fields(client, doc_id)["policy_number"]["value"] == "FS-9999"


def test_second_edit_keeps_the_first_original(client):
    doc_id = _upload(client, POLICY_TEXT)
    _patch(client, doc_id, "policy_number", "FS-1111")
    body = _patch(client, doc_id, "policy_number", "FS-2222").json()
    assert (body["value"], body["original_value"]) == ("FS-2222", "FS-2024-001")


def test_not_found_field_can_be_filled(client):
    doc_id = _upload(client, "Póliza de hogar\nNúmero de póliza: FS-3003")
    assert _fields(client, doc_id)["license_plate"]["status"] == "not_found"
    body = _patch(client, doc_id, "license_plate", "5678-CDF").json()
    assert body["status"] == "edited"
    assert body["original_value"] is None


def test_values_are_normalized_like_the_llm_output(client):
    doc_id = _upload(client, INVOICE_TEXT)
    body = _patch(client, doc_id, "invoice_amount", {"amount": "99.9", "currency": "usd"}).json()
    assert body["value"] == {"amount": "99.9", "currency": "USD"}
    body = _patch(client, doc_id, "invoice_date", "2026-01-31").json()
    assert body["value"] == "2026-01-31"


def test_period_and_list_values(client):
    doc_id = _upload(client, POLICY_TEXT)
    body = _patch(client, doc_id, "validity", {"start": "2026-01-01", "end": "2026-12-31"}).json()
    assert body["value"] == {"start": "2026-01-01", "end": "2026-12-31"}
    body = _patch(client, doc_id, "coverages", ["Robo", "Incendio"]).json()
    assert body["value"] == ["Robo", "Incendio"]


def test_edited_value_is_used_by_the_chat_filters(client):
    doc_id = _upload(client, POLICY_TEXT)
    _patch(client, doc_id, "policy_number", "FS-5555")
    new = client.post("/ask", json={"question": "documentos de la póliza FS-5555"}).json()
    old = client.post("/ask", json={"question": "documentos de la póliza FS-2024-001"}).json()
    assert [d["id"] for d in new["documents"]] == [doc_id]
    assert old["documents"] == []


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("validity", {"start": "2026-12-31", "end": "2026-01-01"}),
        ("validity", "2026"),
        ("invoice_amount", {"amount": -1, "currency": "EUR"}),
        ("policy_number", "x" * 65),
        ("coverages", "Robo"),
    ],
)
def test_invalid_values_return_422_with_a_readable_message(client, name, value):
    doc_id = _upload(client, POLICY_TEXT if name != "invoice_amount" else INVOICE_TEXT)
    response = _patch(client, doc_id, name, value)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "invalid_field_value"
    assert name in error["message"]


@pytest.mark.parametrize("value", [None, "", "   ", []])
def test_empty_values_are_rejected(client, value):
    doc_id = _upload(client, POLICY_TEXT)
    response = _patch(client, doc_id, "policy_number", value)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_field_value"


def test_rejected_edit_changes_nothing(client):
    doc_id = _upload(client, POLICY_TEXT)
    _patch(client, doc_id, "validity", "no es un periodo")
    assert _fields(client, doc_id)["validity"]["status"] == "ok"


@pytest.mark.parametrize("name", ["invoice_amount", "document_type", "nombre_raro"])
def test_fields_not_editable_for_the_type_return_404(client, name):
    doc_id = _upload(client, POLICY_TEXT)
    response = _patch(client, doc_id, name, "x")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "field_not_found"


def test_unknown_document_returns_404(client):
    response = _patch(client, "00000000-0000-0000-0000-000000000000", "policy_number", "x")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "document_not_found"


def test_document_not_processed_returns_409(client):
    doc_id = _upload(client, "", "")  # No text: failed.
    response = _patch(client, doc_id, "policy_number", "FS-1")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "document_not_ready"


def test_missing_body_returns_422(client):
    doc_id = _upload(client, POLICY_TEXT)
    assert client.patch(f"/documents/{doc_id}/fields/policy_number", json={}).status_code == 422
