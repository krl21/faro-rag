"""PDF attachments: LiteLLM message format, fake provider and tracing."""

import base64
import json

import litellm
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.ai.providers import traced
from app.ai.providers.fake_provider import FakeLLMProvider
from app.ai.providers.litellm_provider import LiteLLMChatProvider, to_litellm_message
from app.ai.providers.traced import TracedLLMProvider
from app.ai.providers.types import Attachment, ChatMessage
from tests.fixtures.pdf_factory import POLICY_TEXT, make_pdf

PDF = make_pdf([POLICY_TEXT])
ATTACHMENT = Attachment(data=PDF, mime_type="application/pdf", filename="poliza.pdf")


def test_plain_message_keeps_string_content():
    assert to_litellm_message(ChatMessage(role="user", content="hola")) == {
        "role": "user",
        "content": "hola",
    }


def test_attachment_becomes_a_base64_file_part():
    message = to_litellm_message(
        ChatMessage(role="user", content="extrae", attachments=(ATTACHMENT,))
    )
    text_part, file_part = message["content"]
    assert text_part == {"type": "text", "text": "extrae"}
    assert file_part["type"] == "file"
    assert file_part["file"]["filename"] == "poliza.pdf"
    prefix, encoded = file_part["file"]["file_data"].split(",", 1)
    assert prefix == "data:application/pdf;base64"
    assert base64.b64decode(encoded) == PDF


def test_litellm_provider_sends_the_attachment(monkeypatch):
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return litellm.ModelResponse(choices=[{"message": {"content": "{}"}}])

    monkeypatch.setattr(litellm, "completion", fake_completion)
    LiteLLMChatProvider("gemini/gemini-1.5-flash", timeout_seconds=5).complete(
        [ChatMessage(role="user", content="extrae", attachments=(ATTACHMENT,))],
        purpose="extract.policy",
    )
    assert captured["messages"][0]["content"][1]["type"] == "file"


def test_fake_provider_reads_the_attached_pdf():
    response = FakeLLMProvider().complete(
        [ChatMessage(role="user", content="extrae", attachments=(ATTACHMENT,))],
        purpose="extract.policy",
    )
    assert json.loads(response.text)["numero_poliza"]["valor"] == "FS-2024-001"


def test_fake_provider_without_pdf_finds_nothing():
    response = FakeLLMProvider().complete(
        [ChatMessage(role="user", content="extrae")], purpose="extract.policy"
    )
    assert json.loads(response.text)["numero_poliza"]["valor"] is None


def test_fake_provider_ignores_non_pdf_attachments():
    image = Attachment(data=b"\x89PNG", mime_type="image/png")
    response = FakeLLMProvider().complete(
        [ChatMessage(role="user", content="extrae", attachments=(image,))],
        purpose="extract.policy",
    )
    assert json.loads(response.text)["numero_poliza"]["valor"] is None


def test_span_records_attachment_count_and_size(monkeypatch):
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(traced, "get_tracer", lambda: provider.get_tracer("test"))

    TracedLLMProvider(FakeLLMProvider()).complete(
        [ChatMessage(role="user", content="extrae", attachments=(ATTACHMENT,))],
        purpose="extract.policy",
    )
    (span,) = exporter.get_finished_spans()
    assert span.attributes["llm.attachments.count"] == 1
    assert span.attributes["llm.attachments.bytes"] == len(PDF)


def test_span_has_no_attachment_attributes_without_files(monkeypatch):
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(traced, "get_tracer", lambda: provider.get_tracer("test"))

    TracedLLMProvider(FakeLLMProvider()).complete(
        [ChatMessage(role="user", content="hola")], purpose="answer"
    )
    (span,) = exporter.get_finished_spans()
    assert "llm.attachments.count" not in span.attributes
