"""The upload and question flows log each step (INFO) and its detail (DEBUG)."""

import logging

import pytest

from tests.fixtures.pdf_factory import POLICY_TEXT, make_pdf

pytestmark = pytest.mark.integration


def _messages(caplog, level=logging.INFO) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.levelno == level]


def test_upload_logs_every_step(client, caplog):
    with caplog.at_level(logging.INFO):
        client.post(
            "/documents", files={"file": ("p.pdf", make_pdf([POLICY_TEXT]), "application/pdf")}
        )
    info = _messages(caplog)
    for step in (
        "upload validated",
        "document created",
        "document enqueued",
        "document task started",
        "document processing started",
        "text extracted",
        "llm call finished",
        "document classified",
        "text chunked",
        "chunks embedded",
        "fields extracted",
        "processing result stored",
        "document processed",
        "document task finished",
        "request handled",
    ):
        assert step in info, f"missing INFO log: {step}"


def test_steps_carry_their_outputs(client, caplog):
    with caplog.at_level(logging.INFO):
        client.post(
            "/documents", files={"file": ("p.pdf", make_pdf([POLICY_TEXT]), "application/pdf")}
        )
    by_message = {r.getMessage(): r for r in caplog.records}
    classified = by_message["document classified"]
    assert classified.document_type == "policy"
    assert classified.duration_ms >= 0
    assert by_message["text chunked"].chunks >= 1
    assert by_message["fields extracted"].fields_ok >= 1
    assert by_message["request handled"].status_code == 202


def test_debug_logs_the_content_but_never_pdf_bytes(client, caplog):
    with caplog.at_level(logging.DEBUG):
        client.post(
            "/documents", files={"file": ("p.pdf", make_pdf([POLICY_TEXT]), "application/pdf")}
        )
    by_message = {r.getMessage(): r for r in caplog.records}
    assert "FS-2024-001" in str(by_message["extracted text by page"].pages)
    request = by_message["llm request"]
    attachment = request.messages[-1]["attachments"][0]
    assert attachment["mime_type"] == "application/pdf"
    assert "%PDF" not in str(request.messages)


def test_rejected_upload_logs_a_warning(client, caplog):
    with caplog.at_level(logging.INFO):
        client.post("/documents", files={"file": ("x.txt", b"hola", "text/plain")})
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warnings[0].getMessage() == "upload rejected"
    assert warnings[0].reason == "invalid_file_type"


def test_question_logs_interpretation_retrieval_and_answer(client, caplog):
    client.post("/documents", files={"file": ("p.pdf", make_pdf([POLICY_TEXT]), "application/pdf")})
    caplog.clear()
    with caplog.at_level(logging.INFO):
        client.post("/ask", json={"question": "¿qué coberturas incluye la póliza?"})
    info = _messages(caplog)
    for step in (
        "conversation created",
        "question interpreted",
        "fragments retrieved",
        "answer generated",
        "question answered",
    ):
        assert step in info, f"missing INFO log: {step}"


def test_invalid_llm_answer_is_logged_as_warning(caplog):
    import json

    from app.ai.extraction.field_extractor import FieldExtractor
    from app.ai.providers.fake_provider import FakeLLMProvider
    from app.ai.providers.traced import TracedLLMProvider
    from app.domain.dtos import LLMDocument

    llm = TracedLLMProvider(
        FakeLLMProvider(
            scripted={
                "classify": ["no es json", json.dumps({"tipo": "poliza", "confianza": "alta"})]
            }
        )
    )
    extractor = FieldExtractor(
        llm, retry_delays=[0, 0], classification_max_chars=100, sleep=lambda _: None
    )
    with caplog.at_level(logging.INFO):
        extractor.classify(
            LLMDocument(pdf=make_pdf([POLICY_TEXT]), filename="p.pdf", text="x", page_count=1)
        )
    (warning,) = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warning.getMessage() == "invalid llm answer"
    assert (warning.purpose, warning.attempt, warning.retries_left) == ("classify", 1, 2)
