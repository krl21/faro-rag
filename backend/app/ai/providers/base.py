"""Provider-agnostic interfaces for chat completion and embeddings."""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from app.ai.providers.types import ChatMessage, LLMResponse


@runtime_checkable
class LLMProvider(Protocol):
    """A chat completion backend."""

    @property
    def model(self) -> str:
        """Name of the model used for completions."""
        ...

    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        purpose: str,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Generate a completion.

        Args:
            messages: Conversation sent to the model.
            purpose: Short label of why the call is made (for example
                ``"answer"`` or ``"extract.policy"``). Recorded in traces and
                used by the fake provider to pick a deterministic reply.
            json_mode: Ask the model to return a JSON object.

        Returns:
            The generated response.

        Raises:
            ProviderTimeoutError: If the call exceeds the configured timeout.
            ProviderError: If the provider fails for any other reason.
        """
        ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """A text embedding backend."""

    @property
    def model(self) -> str:
        """Name of the embedding model."""
        ...

    @property
    def dimension(self) -> int:
        """Length of every vector returned by ``embed``."""
        ...

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed a batch of texts.

        Args:
            texts: Texts to embed.

        Returns:
            One vector per input text, in the same order.

        Raises:
            ProviderTimeoutError: If the call exceeds the configured timeout.
            ProviderError: If the provider fails for any other reason.
        """
        ...
