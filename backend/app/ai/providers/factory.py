"""Build the configured providers."""

from functools import lru_cache

from app.ai.providers.base import EmbeddingProvider, LLMProvider
from app.ai.providers.fake_provider import FakeEmbeddingProvider, FakeLLMProvider
from app.ai.providers.traced import TracedEmbeddingProvider, TracedLLMProvider
from app.config import Settings, get_settings
from app.domain.enums import EmbeddingProviderName, LLMProviderName


def build_llm_provider(settings: Settings) -> LLMProvider:
    """Create the chat provider selected by ``LLM_PROVIDER``.

    Args:
        settings: Application settings.

    Returns:
        The provider, wrapped with tracing.
    """
    if settings.llm_provider is LLMProviderName.FAKE:
        inner: LLMProvider = FakeLLMProvider()
    else:
        from app.ai.providers.litellm_provider import LiteLLMChatProvider

        inner = LiteLLMChatProvider(
            settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
            temperature=settings.llm_temperature,
            api_key=settings.llm_api_key,
            api_base=settings.llm_api_base,
        )
    return TracedLLMProvider(inner)


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Create the embedding provider selected by ``EMBEDDING_PROVIDER``.

    Args:
        settings: Application settings.

    Returns:
        The provider, wrapped with tracing.
    """
    if settings.embedding_provider is EmbeddingProviderName.FAKE:
        inner: EmbeddingProvider = FakeEmbeddingProvider(settings.embedding_dim)
    elif settings.embedding_provider is EmbeddingProviderName.SENTENCE_TRANSFORMERS:
        from app.ai.providers.sentence_transformers_provider import (
            SentenceTransformersEmbeddingProvider,
        )

        inner = SentenceTransformersEmbeddingProvider(
            settings.embedding_model, batch_size=settings.embedding_batch_size
        )
    else:
        from app.ai.providers.litellm_provider import LiteLLMEmbeddingProvider

        inner = LiteLLMEmbeddingProvider(
            settings.embedding_model,
            dimension=settings.embedding_dim,
            timeout_seconds=settings.embedding_timeout_seconds,
            api_key=settings.embedding_api_key,
            api_base=settings.embedding_api_base,
        )
    return TracedEmbeddingProvider(inner)


@lru_cache
def get_llm_provider() -> LLMProvider:
    """Return the process-wide chat provider.

    Returns:
        The cached provider.
    """
    return build_llm_provider(get_settings())


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    """Return the process-wide embedding provider.

    Returns:
        The cached provider.
    """
    return build_embedding_provider(get_settings())
