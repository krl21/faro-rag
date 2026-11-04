"""Startup check that warns when the LLM may not accept PDF input."""

import logging

import litellm.utils
import pytest

from app.config import get_settings
from app.core.startup_checks import check_pdf_input
from app.domain.enums import DocumentInput, LLMProviderName


def _settings(model: str, provider=LLMProviderName.LITELLM):
    return get_settings().model_copy(update={"llm_provider": provider, "llm_model": model})


def test_fake_provider_always_passes():
    assert check_pdf_input(_settings("fake-llm", LLMProviderName.FAKE)) is True


def test_model_with_pdf_input_passes(monkeypatch, caplog):
    monkeypatch.setattr(litellm.utils, "supports_pdf_input", lambda model: True)
    with caplog.at_level(logging.INFO):
        assert check_pdf_input(_settings("gemini/gemini-2.5-flash")) is True
    assert "pdf input check passed" in caplog.text


def test_model_without_pdf_input_only_warns(monkeypatch, caplog):
    monkeypatch.setattr(litellm.utils, "supports_pdf_input", lambda model: False)
    assert check_pdf_input(_settings("ollama/llama3")) is False
    assert "may not accept PDF input" in caplog.text
    assert caplog.records[-1].levelno == logging.WARNING


@pytest.mark.parametrize("error", [ValueError("unknown model"), RuntimeError("boom")])
def test_check_failure_is_a_warning(monkeypatch, caplog, error):
    def broken(model):
        raise error

    monkeypatch.setattr(litellm.utils, "supports_pdf_input", broken)
    assert check_pdf_input(_settings("x/y")) is False
    assert "pdf input check could not run" in caplog.text


def test_text_mode_does_not_need_pdf_input(monkeypatch, caplog):
    def must_not_be_called(model):
        raise AssertionError("not needed in text mode")

    monkeypatch.setattr(litellm.utils, "supports_pdf_input", must_not_be_called)
    settings = _settings("ollama/llama3").model_copy(
        update={"llm_document_input": DocumentInput.TEXT}
    )
    with caplog.at_level(logging.INFO):
        assert check_pdf_input(settings) is True
    assert "documents are sent as text" in caplog.text


def test_pdf_mode_warning_suggests_text_mode(monkeypatch, caplog):
    monkeypatch.setattr(litellm.utils, "supports_pdf_input", lambda model: False)
    check_pdf_input(_settings("ollama/llama3"))
    assert "LLM_DOCUMENT_INPUT=text" in caplog.text
