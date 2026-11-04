import pytest

from tests.fixtures.pdf_factory import CORRUPT_PDF, INVOICE_TEXT, POLICY_TEXT, make_pdf

pytestmark = pytest.mark.integration


def _upload(client, content: bytes, filename: str = "poliza.pdf"):
    return client.post("/documents", files={"file": (filename, content, "application/pdf")})


def _fields(detail: dict) -> dict:
    return {f["name"]: f for f in detail["fields"]}


def test_upload_processes_policy_and_exposes_fields(client):
    response = _upload(client, make_pdf([POLICY_TEXT]))
    assert response.status_code == 202
    body = response.json()
    assert body["duplicate"] is False

    detail = client.get(f"/documents/{body['id']}").json()
    assert detail["status"] == "done"
    assert detail["document_type"] == "policy"
    assert detail["page_count"] == 1
    assert detail["chunk_count"] >= 1
    fields = _fields(detail)
    assert fields["policy_number"]["value"] == "FS-2024-001"
    assert fields["policy_number"]["confidence"] == "high"
    assert fields["validity"]["value"] == {"start": "2025-01-01", "end": "2025-12-31"}


def test_invoice_amount_is_extracted(client):
    doc_id = _upload(client, make_pdf([INVOICE_TEXT]), "factura.pdf").json()["id"]
    fields = _fields(client.get(f"/documents/{doc_id}").json())
    assert fields["invoice_amount"]["value"] == {"amount": "1250.50", "currency": "EUR"}


def test_duplicate_upload_returns_existing_document(client):
    content = make_pdf([POLICY_TEXT])
    first = _upload(client, content).json()
    second = _upload(client, content, "copia.pdf")
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert second.json()["id"] == first["id"]
    assert first["id"] in second.json()["message"]
    assert len(client.get("/documents").json()) == 1


def test_corrupt_pdf_is_marked_failed(client):
    doc_id = _upload(client, CORRUPT_PDF).json()["id"]
    detail = client.get(f"/documents/{doc_id}").json()
    assert detail["status"] == "failed"
    assert detail["error"]["code"] == "corrupt_pdf"


def test_pdf_without_text_is_marked_failed(client):
    doc_id = _upload(client, make_pdf(["", ""])).json()["id"]
    detail = client.get(f"/documents/{doc_id}").json()
    assert detail["status"] == "failed"
    assert detail["error"]["code"] == "no_extractable_text"


def test_non_pdf_is_rejected_synchronously(client):
    response = client.post("/documents", files={"file": ("a.pdf", b"hola", "application/pdf")})
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "invalid_file_type"


def test_unknown_document_returns_404(client):
    response = client.get("/documents/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_list_documents(client):
    _upload(client, make_pdf([POLICY_TEXT]))
    _upload(client, make_pdf([INVOICE_TEXT]), "factura.pdf")
    listing = client.get("/documents").json()
    assert {d["filename"] for d in listing} == {"poliza.pdf", "factura.pdf"}
    assert all(d["status"] == "done" for d in listing)
