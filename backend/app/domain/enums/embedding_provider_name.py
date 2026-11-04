"""Available embedding providers (``EMBEDDING_PROVIDER``)."""

from enum import StrEnum


class EmbeddingProviderName(StrEnum):
    """Available embedding providers (``EMBEDDING_PROVIDER``)."""

    SENTENCE_TRANSFORMERS = "sentence_transformers"
    LITELLM = "litellm"
    FAKE = "fake"
