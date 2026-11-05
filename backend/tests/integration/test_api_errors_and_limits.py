"""HTTP-level negative cases: validation, limits, rate limiting and health."""

import pytest

from tests.fixtures.pdf_factory import POLICY_TEXT, make_pdf

pytestmark = pytest.mark.integration


def _upload(client, content: bytes, filename="a.pdf", content_type="application/pdf"):
    return client.post("/documents", files={"file": (filename, content, content_type)})


def test_liveness(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_readiness_checks_database_redis_and_worker(client, monkeypatch):
    from app.worker.celery_app import celery_app

    monkeypatch.setattr(celery_app.control, "ping", lambda timeout: [{"celery@w": {"ok": "pong"}}])
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"database": "ok", "redis": "ok", "worker": "ok"}


def test_readiness_without_worker_is_503(client, monkeypatch):
    from app.worker.celery_app import celery_app

    monkeypatch.setattr(celery_app.control, "ping", lambda timeout: [])
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["worker"] == "error"


def test_readiness_when_the_worker_ping_fails(client, monkeypatch):
    from app.worker.celery_app import celery_app

    def broken(timeout):
        raise ConnectionError("broker down")

    monkeypatch.setattr(celery_app.control, "ping", broken)
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["worker"] == "error"


def test_file_over_the_size_limit_returns_413(client, settings, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_mb", 1)
    content = make_pdf([POLICY_TEXT]) + b"0" * (1024 * 1024)
    response = _upload(client, content)
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"
    assert client.get("/documents").json() == []


def test_empty_file_returns_400(client):
    response = _upload(client, b"")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "empty_file"


def test_wrong_extension_returns_415(client):
    assert _upload(client, make_pdf(["x"]), filename="poliza.docx").status_code == 415


def test_wrong_content_type_returns_415(client):
    assert _upload(client, make_pdf(["x"]), content_type="text/plain").status_code == 415


def test_missing_file_field_returns_422(client):
    assert client.post("/documents").status_code == 422


def test_too_many_pages_is_marked_failed(client, settings, monkeypatch):
    monkeypatch.setattr(settings, "max_pages", 1)
    doc_id = _upload(client, make_pdf([POLICY_TEXT, POLICY_TEXT])).json()["id"]
    detail = client.get(f"/documents/{doc_id}").json()
    assert detail["status"] == "failed"
    assert detail["error"]["code"] == "too_many_pages"
    assert detail["chunk_count"] == 0


def test_duplicate_of_a_failed_document_is_processed_again(client):
    first = _upload(client, make_pdf(["", ""])).json()
    assert client.get(f"/documents/{first['id']}").json()["status"] == "failed"
    response = _upload(client, make_pdf(["", ""]))
    second = response.json()
    assert response.status_code == 202
    assert second["duplicate"] is True
    assert second["id"] == first["id"]
    assert "queued again" in second["message"]
    # Still no text, so the retry fails again with the same permanent error.
    detail = client.get(f"/documents/{first['id']}").json()
    assert detail["status"] == "failed"
    assert detail["error"]["code"] == "no_extractable_text"


def test_invalid_document_id_returns_422(client):
    assert client.get("/documents/no-es-un-uuid").status_code == 422


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 500}, {"offset": -1}])
def test_invalid_pagination_returns_422(client, params):
    assert client.get("/documents", params=params).status_code == 422


def test_pagination_limits_and_offsets(client):
    for i in range(3):
        _upload(client, make_pdf([f"{POLICY_TEXT}\nAnexo {i}"]), filename=f"p{i}.pdf")
    first_page = client.get("/documents", params={"limit": 2}).json()
    second_page = client.get("/documents", params={"limit": 2, "offset": 2}).json()
    assert len(first_page) == 2
    assert len(second_page) == 1
    assert {d["id"] for d in first_page}.isdisjoint({d["id"] for d in second_page})


@pytest.mark.parametrize(
    "body",
    [{}, {"question": "ab"}, {"question": "x" * 1001}, {"question": "ok?", "document_id": "x"}],
)
def test_invalid_ask_body_returns_422(client, body):
    assert client.post("/ask", json=body).status_code == 422


def test_ask_on_unknown_document_has_no_evidence(client):
    _upload(client, make_pdf([POLICY_TEXT]))
    body = client.post(
        "/ask",
        json={
            "question": "número de póliza",
            "document_id": "00000000-0000-0000-0000-000000000000",
        },
    ).json()
    assert body["answered"] is False


def test_ask_without_documents_has_no_evidence(client):
    assert client.post("/ask", json={"question": "número de póliza"}).json()["answered"] is False


def test_ask_is_rate_limited(client, settings, monkeypatch):
    monkeypatch.setattr(settings, "ask_rate_limit", "2/minute")
    codes = [client.post("/ask", json={"question": "hola mundo"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]
    assert client.post("/ask", json={"question": "hola"}).json()["error"]["code"] == "rate_limited"
