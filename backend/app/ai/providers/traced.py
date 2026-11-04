"""Tracing wrappers that add OpenTelemetry spans to any provider."""

import logging
import time
from collections.abc import Sequence

from opentelemetry.trace import Status, StatusCode

from app.ai.providers.base import EmbeddingProvider, LLMProvider
from app.ai.providers.types import ChatMessage, LLMResponse
from app.core.flow_logging import fields
from app.core.telemetry import get_tracer

logger = logging.getLogger(__name__)


def _messages_for_log(messages: Sequence[ChatMessage]) -> list[dict[str, object]]:
    """Describe the messages for a DEBUG log: full text, attachments as metadata only.

    Args:
        messages: Conversation sent to the model.

    Returns:
        One entry per message; PDF bytes are never included.
    """
    return [
        {
            "role": m.role,
            "content": m.content,
            "attachments": [
                {"filename": a.filename, "mime_type": a.mime_type, "bytes": len(a.data)}
                for a in m.attachments
            ],
        }
        for m in messages
    ]


class TracedLLMProvider:
    """Wrap an ``LLMProvider`` so every call produces an ``llm.complete`` span.

    Span attributes follow the OpenTelemetry GenAI conventions where possible:
    model, purpose, latency and input/output tokens.
    """

    def __init__(self, inner: LLMProvider) -> None:
        """Create the wrapper.

        Args:
            inner: Provider that performs the call.
        """
        self._inner = inner

    @property
    def model(self) -> str:
        """Name of the wrapped model."""
        return self._inner.model

    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        purpose: str,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Call the wrapped provider inside a span.

        Args:
            messages: Conversation sent to the model.
            purpose: Call label, recorded as ``llm.purpose``.
            json_mode: Ask the model to return a JSON object.

        Returns:
            The wrapped provider's response.
        """
        with get_tracer().start_as_current_span("llm.complete") as span:
            span.set_attribute("gen_ai.request.model", self._inner.model)
            span.set_attribute("llm.purpose", purpose)
            attachments = [a for m in messages for a in m.attachments]
            if attachments:
                span.set_attribute("llm.attachments.count", len(attachments))
                span.set_attribute("llm.attachments.bytes", sum(len(a.data) for a in attachments))
            logger.debug(
                "llm request",
                extra=fields(
                    purpose=purpose,
                    model=self._inner.model,
                    json_mode=json_mode,
                    messages=_messages_for_log(messages),
                ),
            )
            started = time.perf_counter()
            try:
                response = self._inner.complete(messages, purpose=purpose, json_mode=json_mode)
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                logger.warning(
                    "llm call failed",
                    extra=fields(
                        purpose=purpose,
                        model=self._inner.model,
                        latency_ms=round((time.perf_counter() - started) * 1000),
                        error_type=type(exc).__name__,
                        error=str(exc),
                    ),
                )
                raise
            finally:
                span.set_attribute("llm.latency_ms", round((time.perf_counter() - started) * 1000))
            span.set_attribute("gen_ai.response.model", response.model)
            if response.input_tokens is not None:
                span.set_attribute("gen_ai.usage.input_tokens", response.input_tokens)
            if response.output_tokens is not None:
                span.set_attribute("gen_ai.usage.output_tokens", response.output_tokens)
            logger.info(
                "llm call finished",
                extra=fields(
                    purpose=purpose,
                    model=response.model,
                    messages=len(messages),
                    attachments=len(attachments),
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    latency_ms=round((time.perf_counter() - started) * 1000),
                ),
            )
            logger.debug("llm response", extra=fields(purpose=purpose, response=response.text))
            return response


class TracedEmbeddingProvider:
    """Wrap an ``EmbeddingProvider`` so every call produces an ``embedding.embed`` span."""

    def __init__(self, inner: EmbeddingProvider) -> None:
        """Create the wrapper.

        Args:
            inner: Provider that performs the call.
        """
        self._inner = inner

    @property
    def model(self) -> str:
        """Name of the wrapped model."""
        return self._inner.model

    @property
    def dimension(self) -> int:
        """Vector length of the wrapped provider."""
        return self._inner.dimension

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Call the wrapped provider inside a span.

        Args:
            texts: Texts to embed.

        Returns:
            The wrapped provider's vectors.
        """
        with get_tracer().start_as_current_span("embedding.embed") as span:
            span.set_attribute("embedding.model", self._inner.model)
            span.set_attribute("embedding.batch_size", len(texts))
            started = time.perf_counter()
            try:
                vectors = self._inner.embed(texts)
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                logger.warning(
                    "embedding call failed",
                    extra=fields(
                        model=self._inner.model,
                        texts=len(texts),
                        error_type=type(exc).__name__,
                        error=str(exc),
                    ),
                )
                raise
            else:
                logger.debug(
                    "embedding call finished",
                    extra=fields(
                        model=self._inner.model,
                        texts=len(texts),
                        latency_ms=round((time.perf_counter() - started) * 1000),
                    ),
                )
                return vectors
            finally:
                span.set_attribute(
                    "embedding.latency_ms", round((time.perf_counter() - started) * 1000)
                )
