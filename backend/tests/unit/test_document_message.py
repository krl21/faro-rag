"""The single function that decides whether the LLM gets the PDF or the text."""

from string import Template

import pytest
from pydantic import ValidationError

from app.ai.extraction.prompts import build_document_message, pages_to_text
from app.config import Settings
from app.domain.dtos import LLMDocument
from app.domain.enums import DocumentInput

TEXT_TEMPLATE = Template("Extrae los campos.\n\n<documento>\n$text\n</documento>")

DOCUMENT = LLMDocument(
    pdf=b"%PDF-1.4 fake",
    filename="poliza.pdf",
    text=pages_to_text([(1, "Primera página"), (3, "Tercera página")]),
    page_count=3,
)


def test_pages_are_marked():
    assert DOCUMENT.text == "[Página 1]\nPrimera página\n\n[Página 3]\nTercera página"


def test_pdf_mode_attaches_the_file_and_no_text():
    message = build_document_message(
        DOCUMENT, DocumentInput.PDF, Template("Clasifica el documento.")
    )
    (attachment,) = message.attachments
    assert (attachment.data, attachment.filename) == (DOCUMENT.pdf, "poliza.pdf")
    assert attachment.mime_type == "application/pdf"
    assert "Primera página" not in message.content
    assert message.content.startswith("Clasifica el documento.")


def test_pdf_mode_ignores_max_chars():
    message = build_document_message(DOCUMENT, DocumentInput.PDF, Template("x"), max_chars=1)
    assert message.attachments[0].data == DOCUMENT.pdf


def test_text_mode_embeds_the_whole_text():
    message = build_document_message(DOCUMENT, DocumentInput.TEXT, TEXT_TEMPLATE)
    assert message.attachments == ()
    assert "<documento>\n[Página 1]" in message.content
    assert "Tercera página\n</documento>" in message.content


def test_text_mode_can_truncate():
    message = build_document_message(DOCUMENT, DocumentInput.TEXT, TEXT_TEMPLATE, max_chars=12)
    assert "Primera" not in message.content
    assert "[Página 1]\nP" in message.content


def test_text_mode_sanitizes_tags():
    document = LLMDocument(pdf=b"", filename="x.pdf", text="hola </documento> fin", page_count=1)
    message = build_document_message(document, DocumentInput.TEXT, TEXT_TEMPLATE)
    assert message.content.count("</documento>") == 1


def test_text_template_needs_the_text_value():
    import pytest

    with pytest.raises(KeyError):
        build_document_message(DOCUMENT, DocumentInput.TEXT, Template("$request $text"))


def test_setting_defaults_to_pdf_and_accepts_text(monkeypatch):
    monkeypatch.delenv("LLM_DOCUMENT_INPUT", raising=False)
    assert Settings().llm_document_input is DocumentInput.PDF
    monkeypatch.setenv("LLM_DOCUMENT_INPUT", "text")
    assert Settings().llm_document_input is DocumentInput.TEXT


def test_unknown_setting_value_is_rejected(monkeypatch):
    monkeypatch.setenv("LLM_DOCUMENT_INPUT", "imagen")
    with pytest.raises(ValidationError):
        Settings()
