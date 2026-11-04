"""Available chat completion providers (``LLM_PROVIDER``)."""

from enum import StrEnum


class LLMProviderName(StrEnum):
    """Available chat completion providers (``LLM_PROVIDER``)."""

    LITELLM = "litellm"
    FAKE = "fake"
