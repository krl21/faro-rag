"""LiteLLM-backed providers: one code path for Gemini, OpenAI, Anthropic, etc."""

import base64
from collections.abc import Sequence
from typing import Any

import litellm

from app.ai.providers.types import ChatMessage, LLMResponse
from app.core.errors import ProviderError, ProviderTimeoutError


def to_litellm_message(message: ChatMessage) -> dict[str, Any]:
    """Convert a message to the OpenAI-style format LiteLLM expects.

    Messages without attachments keep a plain string ``content``. With
    attachments, ``content`` becomes a list with the text part followed by one
    ``file`` part per attachment, encoded as a base64 data URL. LiteLLM
    translates that part to each provider's native format (Gemini, Anthropic,
    OpenAI, Bedrock...).

    Args:
        message: Message to convert.

    Returns:
        The LiteLLM message dictionary.
    """
    if not message.attachments:
        return {"role": message.role, "content": message.content}
    parts: list[dict[str, Any]] = [{"type": "text", "text": message.content}]
    for attachment in message.attachments:
        encoded = base64.b64encode(attachment.data).decode("ascii")
        parts.append(
            {
                "type": "file",
                "file": {
                    "file_data": f"data:{attachment.mime_type};base64,{encoded}",
                    "filename": attachment.filename,
                },
            }
        )
    return {"role": message.role, "content": parts}


class LiteLLMChatProvider:
    """Chat completion through LiteLLM.

    The provider is selected by the model prefix, for example
    ``gemini/gemini-2.5-flash`` or ``openai/gpt-4o-mini``.
    """

    def __init__(
        self,
        model: str,
        *,
        timeout_seconds: float,
        temperature: float = 0.0,
        api_key: str | None = None,
        api_base: str | None = None,
    ) -> None:
        """Create the provider.

        Args:
            model: LiteLLM model identifier.
            timeout_seconds: Maximum duration of one call.
            temperature: Sampling temperature.
            api_key: Provider API key.
            api_base: Custom endpoint, for self-hosted or proxied models.
        """
        self._model = model
        self._timeout = timeout_seconds
        self._temperature = temperature
        self._api_key = api_key
        self._api_base = api_base

    @property
    def model(self) -> str:
        """Name of the model used for completions."""
        return self._model

    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        purpose: str,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Generate a completion with LiteLLM.

        Args:
            messages: Conversation sent to the model. Attachments require a
                model with file (PDF) input.
            purpose: Call label (unused here; recorded by the tracing wrapper).
            json_mode: Ask the model to return a JSON object.

        Returns:
            The generated response with token usage.

        Raises:
            ProviderTimeoutError: If the call exceeds the timeout.
            ProviderError: If LiteLLM or the provider fails.
        """
        kwargs: dict = {
            "model": self._model,
            "messages": [to_litellm_message(m) for m in messages],
            "timeout": self._timeout,
            "temperature": self._temperature,
            "api_key": self._api_key,
            "api_base": self._api_base,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            response = litellm.completion(**kwargs)
        except litellm.exceptions.Timeout as exc:
            raise ProviderTimeoutError(f"LLM call timed out after {self._timeout}s") from exc
        except Exception as exc:
            raise ProviderError(f"LLM call failed: {exc}") from exc

        usage = getattr(response, "usage", None)
        return LLMResponse(
            text=response.choices[0].message.content or "",
            model=response.model or self._model,
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
        )


class LiteLLMEmbeddingProvider:
    """Embeddings through LiteLLM (remote APIs)."""

    def __init__(
        self,
        model: str,
        *,
        dimension: int,
        timeout_seconds: float,
        api_key: str | None = None,
        api_base: str | None = None,
    ) -> None:
        """Create the provider.

        Args:
            model: LiteLLM embedding model identifier.
            dimension: Expected vector length (must match the database column).
            timeout_seconds: Maximum duration of one call.
            api_key: Provider API key.
            api_base: Custom endpoint.
        """
        self._model = model
        self._dimension = dimension
        self._timeout = timeout_seconds
        self._api_key = api_key
        self._api_base = api_base

    @property
    def model(self) -> str:
        """Name of the embedding model."""
        return self._model

    @property
    def dimension(self) -> int:
        """Configured vector length."""
        return self._dimension

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed a batch of texts with LiteLLM.

        Args:
            texts: Texts to embed.

        Returns:
            One vector per input text.

        Raises:
            ProviderTimeoutError: If the call exceeds the timeout.
            ProviderError: If LiteLLM or the provider fails.
        """
        try:
            response = litellm.embedding(
                model=self._model,
                input=list(texts),
                timeout=self._timeout,
                api_key=self._api_key,
                api_base=self._api_base,
            )
        except litellm.exceptions.Timeout as exc:
            raise ProviderTimeoutError(f"Embedding call timed out after {self._timeout}s") from exc
        except Exception as exc:
            raise ProviderError(f"Embedding call failed: {exc}") from exc
        return [list(item["embedding"]) for item in response.data]
