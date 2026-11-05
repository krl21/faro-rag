"""Provider selection by configuration and behaviour when optional extras are missing.

The test image does not install ``sentence-transformers`` or ``docling``, so
these tests also check the errors users get when an extra is missing.
"""

import importlib.util
from pathlib import Path

import pytest

from app.ai.ingestion.docling_extractor import DoclingExtractor
from app.ai.providers.factory import build_embedding_provider, build_llm_provider
from app.ai.providers.fake_provider import FakeEmbeddingProvider, FakeLLMProvider
from app.ai.providers.litellm_provider import LiteLLMChatProvider, LiteLLMEmbeddingProvider
from app.ai.providers.sentence_transformers_provider import SentenceTransformersEmbeddingProvider
from app.config import Settings
from app.core.errors import ExtractorUnavailableError, ProviderError
from tests.fixtures.pdf_factory import make_pdf

HAS_ST = importlib.util.find_spec("sentence_transformers") is not None
HAS_DOCLING = importlib.util.find_spec("docling") is not None


def _inner(provider):
    return provider._inner


@pytest.mark.parametrize(
    ("name", "expected"), [("fake", FakeLLMProvider), ("litellm", LiteLLMChatProvider)]
)
def test_llm_provider_is_selected_by_settings(name, expected):
    assert isinstance(_inner(build_llm_provider(Settings(llm_provider=name))), expected)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("fake", FakeEmbeddingProvider),
        ("litellm", LiteLLMEmbeddingProvider),
        ("sentence_transformers", SentenceTransformersEmbeddingProvider),
    ],
)
def test_embedding_provider_is_selected_by_settings(name, expected):
    provider = build_embedding_provider(Settings(embedding_provider=name))
    assert isinstance(_inner(provider), expected)


def test_unknown_provider_is_rejected_by_settings():
    with pytest.raises(ValueError):
        Settings(llm_provider="openai-directo")


@pytest.mark.skipif(HAS_ST, reason="sentence-transformers is installed in this image")
def test_missing_sentence_transformers_gives_a_clear_error():
    provider = SentenceTransformersEmbeddingProvider("any-model")
    with pytest.raises(ProviderError, match="local-embeddings"):
        provider.embed(["hola"])


@pytest.mark.skipif(HAS_DOCLING, reason="docling is installed in this image")
def test_missing_docling_gives_a_clear_error(tmp_path: Path):
    path = tmp_path / "x.pdf"
    path.write_bytes(make_pdf(["Póliza de prueba"]))
    with pytest.raises(ExtractorUnavailableError, match="docling"):
        DoclingExtractor().extract(path, max_pages=10)
