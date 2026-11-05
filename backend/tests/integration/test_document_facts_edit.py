"""PATCH and DELETE /documents/{id}/facts/{fact_id}: the user corrects or removes a datum."""

import pytest

from tests.fixtures.pdf_factory import INVOICE_TEXT, make_pdf

pytestmark = pytest.mark.integration

EXTRA_PAGE = """Datos del pago
Forma de pago: Transferencia a 30 días
Entidad: Banco del Faro"""


def _upload(client) -> str:
    pdf = make_pdf([INVOICE_TEXT, EXTRA_PAGE])
    return client.post("/documents", files={"file": ("f.pdf", pdf, "application/pdf")}).json()["id"]


def _facts(client, doc_id: str) -> dict[str, dict]:
    return {f["label"]: f for f in client.get(f"/documents/{doc_id}").json()["facts"]}


def test_detail_lists_the_free_data(client):
    doc_id = _upload(client)
    fact = _facts(client, doc_id)["Forma de pago"]
    assert fact["value"] == "Transferencia a 30 días"
    assert fact["page"] == 2
    assert fact["status"] == "ok"
    assert fact["original_value"] is None


def test_value_and_label_are_edited_and_the_original_kept(client):
    doc_id = _upload(client)
    fact_id = _facts(client, doc_id)["Forma de pago"]["id"]
    response = client.patch(
        f"/documents/{doc_id}/facts/{fact_id}",
        json={"label": "Forma de pago acordada", "value": "Domiciliación bancaria"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["label"] == "Forma de pago acordada"
    assert body["value"] == "Domiciliación bancaria"
    assert body["status"] == "edited"
    assert body["original_value"] == {"label": "Forma de pago", "value": "Transferencia a 30 días"}
    # A second edit keeps the value found in the document.
    second = client.patch(f"/documents/{doc_id}/facts/{fact_id}", json={"value": "Efectivo"})
    assert second.json()["original_value"]["value"] == "Transferencia a 30 días"
    assert second.json()["label"] == "Forma de pago acordada"


def test_table_row_can_be_edited(client):
    doc_id = _upload(client)
    fact_id = _facts(client, doc_id)["Entidad"]["id"]
    row = {"Concepto": "Kit", "Importe": "1.280,00 €"}
    body = client.patch(f"/documents/{doc_id}/facts/{fact_id}", json={"value": row}).json()
    assert body["value"] == row


def test_edited_datum_is_used_by_the_chat(client, monkeypatch):
    from app.ai.rag import answerer

    received = []
    original = answerer.build_answer_messages

    def spy(question, fragments, facts=()):
        received.extend(facts)
        return original(question, fragments, facts)

    monkeypatch.setattr(answerer, "build_answer_messages", spy)
    doc_id = _upload(client)
    fact_id = _facts(client, doc_id)["Forma de pago"]["id"]
    client.patch(f"/documents/{doc_id}/facts/{fact_id}", json={"value": "Domiciliación"})
    client.post(f"/documents/{doc_id}/ask", json={"question": "forma de pago"})
    edited = [f for f in received if f.label == "Forma de pago"]
    assert edited and edited[0].value == "Domiciliación" and edited[0].edited


def test_datum_is_deleted(client):
    doc_id = _upload(client)
    fact_id = _facts(client, doc_id)["Forma de pago"]["id"]
    assert client.delete(f"/documents/{doc_id}/facts/{fact_id}").status_code == 204
    assert "Forma de pago" not in _facts(client, doc_id)
    assert (
        client.delete(f"/documents/{doc_id}/facts/{fact_id}").json()["error"]["code"]
        == "fact_not_found"
    )


@pytest.mark.parametrize(
    "body",
    [{"label": "  "}, {"value": ""}, {"value": {"Concepto": " "}}, {"label": "x" * 61}],
)
def test_invalid_edits_are_rejected(client, body):
    doc_id = _upload(client)
    fact_id = _facts(client, doc_id)["Forma de pago"]["id"]
    response = client.patch(f"/documents/{doc_id}/facts/{fact_id}", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_fact_value"


def test_empty_body_is_rejected(client):
    doc_id = _upload(client)
    fact_id = _facts(client, doc_id)["Forma de pago"]["id"]
    assert client.patch(f"/documents/{doc_id}/facts/{fact_id}", json={}).status_code == 422


def test_known_fields_cannot_be_reached_as_free_data(client):
    import uuid

    from sqlalchemy import select

    from app.db.models import ExtractedField
    from app.db.session import session_scope

    doc_id = _upload(client)
    with session_scope() as session:
        known_id = session.scalar(
            select(ExtractedField.id).where(
                ExtractedField.document_id == uuid.UUID(doc_id),
                ExtractedField.is_predefined.is_(True),
            )
        )
    response = client.patch(f"/documents/{doc_id}/facts/{known_id}", json={"value": "x"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "fact_not_found"


def test_unknown_document_gives_404(client):
    response = client.delete("/documents/00000000-0000-0000-0000-000000000000/facts/1")
    assert response.json()["error"]["code"] == "document_not_found"


def test_table_row_keeps_the_order_of_its_columns(client):
    doc_id = _upload(client)
    fact_id = _facts(client, doc_id)["Entidad"]["id"]
    row = {
        "Concepto": "Kit",
        "Cantidad": "1 ud",
        "Precio unit.": "1.280,00 €",
        "Importe": "1.280,00 €",
    }
    client.patch(f"/documents/{doc_id}/facts/{fact_id}", json={"value": row})
    stored = _facts(client, doc_id)["Entidad"]["value"]
    assert list(stored) == ["Concepto", "Cantidad", "Precio unit.", "Importe"]


def test_fixed_field_is_deleted(client):
    doc_id = _upload(client)
    assert client.delete(f"/documents/{doc_id}/fields/invoice_amount").status_code == 204
    names = [f["name"] for f in client.get(f"/documents/{doc_id}").json()["fields"]]
    assert "invoice_amount" not in names
    again = client.delete(f"/documents/{doc_id}/fields/invoice_amount")
    assert again.status_code == 404
    assert again.json()["error"]["code"] == "field_not_found"
    # The filters stop using it: no invoice above 1000 € any more.
    body = client.post("/ask", json={"question": "facturas de más de 1000 euros"}).json()
    assert doc_id not in [d["id"] for d in body.get("documents", [])]


def test_deleted_fixed_field_can_be_filled_in_again(client):
    doc_id = _upload(client)
    client.delete(f"/documents/{doc_id}/fields/holder")
    response = client.patch(f"/documents/{doc_id}/fields/holder", json={"value": "ACME, S.L."})
    assert response.status_code == 200
    assert response.json()["status"] == "edited"


def test_free_datum_with_a_fixed_field_key_is_not_a_filter(client):
    doc_id = _upload(client)
    fact_id = _facts(client, doc_id)["Forma de pago"]["id"]
    client.patch(f"/documents/{doc_id}/facts/{fact_id}", json={"label": "invoice_amount"})
    names = [f["name"] for f in client.get(f"/documents/{doc_id}").json()["fields"]]
    assert names.count("invoice_amount") == 1  # Still only the fixed field.


def test_document_type_can_be_neither_edited_nor_deleted(client):
    doc_id = _upload(client)
    deleted = client.delete(f"/documents/{doc_id}/fields/document_type")
    assert deleted.status_code == 404
    assert deleted.json()["error"]["code"] == "field_not_found"
    edited = client.patch(f"/documents/{doc_id}/fields/document_type", json={"value": "policy"})
    assert edited.status_code == 404
    names = [f["name"] for f in client.get(f"/documents/{doc_id}").json()["fields"]]
    assert "document_type" in names
