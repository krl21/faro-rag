import json
import logging

import pytest
from opentelemetry.sdk.trace import TracerProvider
from pydantic import ValidationError

from app.config import Settings
from app.core.logging import JsonFormatter
from app.services.storage import LocalStorage

# --- Settings ---


def test_defaults_match_the_agreed_values(monkeypatch):
    monkeypatch.delenv("EXTRACTION_RETRY_DELAYS", raising=False)
    settings = Settings()
    assert (settings.chunk_size, settings.chunk_overlap) == (1000, 150)
    assert settings.extraction_retry_delays == [2.0, 6.0]
    assert (settings.llm_timeout_seconds, settings.embedding_timeout_seconds) == (20, 10)
    assert settings.max_upload_bytes == 20 * 1024 * 1024


def test_list_settings_are_read_as_json(monkeypatch):
    monkeypatch.setenv("EXTRACTION_RETRY_DELAYS", "[1, 3]")
    assert Settings().extraction_retry_delays == [1.0, 3.0]


@pytest.mark.parametrize(
    "overrides",
    [
        {"chunk_overlap": 1000},
        {"chunk_size": 0},
        {"max_upload_mb": 0},
        {"retrieval_min_similarity": 1.5},
        {"llm_timeout_seconds": 0},
    ],
)
def test_invalid_settings_are_rejected(overrides):
    with pytest.raises(ValidationError):
        Settings(**overrides)


# --- JSON logging ---


def _record(**extra) -> logging.LogRecord:
    record = logging.makeLogRecord({"name": "test", "levelname": "INFO", "msg": "hola %s"})
    record.args = ("mundo",)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_log_line_is_json_with_extra_fields():
    line = json.loads(JsonFormatter().format(_record(document_id="abc")))
    assert line["message"] == "hola mundo"
    assert line["document_id"] == "abc"
    assert "trace_id" not in line


def test_log_line_includes_active_trace_id():
    tracer = TracerProvider().get_tracer("test")
    with tracer.start_as_current_span("span") as span:
        line = json.loads(JsonFormatter().format(_record()))
    assert line["trace_id"] == format(span.get_span_context().trace_id, "032x")
    assert len(line["span_id"]) == 16


# --- Storage ---


def test_storage_writes_file_named_by_hash(tmp_path):
    path = LocalStorage(tmp_path / "uploads").save("abc123", b"%PDF-1.4")
    assert path.endswith("abc123.pdf")
    assert (tmp_path / "uploads" / "abc123.pdf").read_bytes() == b"%PDF-1.4"
    assert not list((tmp_path / "uploads").glob("*.tmp"))


def test_storage_does_not_rewrite_an_existing_hash(tmp_path):
    storage = LocalStorage(tmp_path)
    first = storage.save("same", b"original")
    second = storage.save("same", b"other")
    assert first == second
    assert (tmp_path / "same.pdf").read_bytes() == b"original"
