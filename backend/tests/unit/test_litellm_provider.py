"""LiteLLM providers with ``litellm`` patched: no network calls are made."""

from types import SimpleNamespace

import litellm
import pytest

from app.ai.providers.litellm_provider import LiteLLMChatProvider, LiteLLMEmbeddingProvider
from app.ai.providers.types import ChatMessage
from app.core.errors import ProviderError, ProviderTimeoutError

MESSAGES = [ChatMessage(role="user", content="hola")]


def _completion_response(text: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        model="gemini/gemini-1.5-flash",
        usage=SimpleNamespace(prompt_tokens=12, completion_tokens=3),
    )


def _chat() -> LiteLLMChatProvider:
    return LiteLLMChatProvider("gemini/gemini-1.5-flash", timeout_seconds=20, api_key="k")


def test_completion_maps_text_and_tokens(monkeypatch):
    captured = {}

    def fake_completion(**kwargs):
        captured.update(kwargs)
        return _completion_response("respuesta")

    monkeypatch.setattr(litellm, "completion", fake_completion)
    response = _chat().complete(MESSAGES, purpose="answer")
    assert response.text == "respuesta"
    assert (response.input_tokens, response.output_tokens) == (12, 3)
    assert captured["timeout"] == 20
    assert captured["messages"] == [{"role": "user", "content": "hola"}]
    assert "response_format" not in captured


def test_json_mode_requests_a_json_object(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        litellm, "completion", lambda **kw: captured.update(kw) or _completion_response("{}")
    )
    _chat().complete(MESSAGES, purpose="classify", json_mode=True)
    assert captured["response_format"] == {"type": "json_object"}


def test_timeout_is_translated(monkeypatch):
    def timeout(**_):
        raise litellm.exceptions.Timeout(message="slow", model="m", llm_provider="gemini")

    monkeypatch.setattr(litellm, "completion", timeout)
    with pytest.raises(ProviderTimeoutError):
        _chat().complete(MESSAGES, purpose="answer")


def test_other_errors_are_translated(monkeypatch):
    def boom(**_):
        raise RuntimeError("401 invalid api key")

    monkeypatch.setattr(litellm, "completion", boom)
    with pytest.raises(ProviderError, match="invalid api key"):
        _chat().complete(MESSAGES, purpose="answer")


def test_embeddings_are_returned_in_order(monkeypatch):
    monkeypatch.setattr(
        litellm,
        "embedding",
        lambda **kw: SimpleNamespace(
            data=[{"embedding": [float(i)] * 3} for i in range(len(kw["input"]))]
        ),
    )
    provider = LiteLLMEmbeddingProvider(
        "gemini/text-embedding-004", dimension=3, timeout_seconds=10
    )
    assert provider.embed(["a", "b"]) == [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]
    assert provider.dimension == 3


def test_embedding_errors_are_translated(monkeypatch):
    def boom(**_):
        raise RuntimeError("quota")

    monkeypatch.setattr(litellm, "embedding", boom)
    provider = LiteLLMEmbeddingProvider("m", dimension=3, timeout_seconds=10)
    with pytest.raises(ProviderError):
        provider.embed(["a"])
