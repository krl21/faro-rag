"""Deterministic fake providers for development and tests (no network calls)."""

import hashlib
import math
import re
import unicodedata
from collections.abc import Callable, Mapping, Sequence

from app.ai.ingestion.pdf_pages import read_text_layer
from app.ai.providers import fake_responses
from app.ai.providers.types import Attachment, ChatMessage, LLMResponse

_TOKEN = re.compile(r"\w+")

_DEFAULT_HANDLERS: dict[str, Callable[[str], str]] = {
    "classify": lambda p: fake_responses.classify(fake_responses.document_text(p)),
    "extract.policy": lambda p: fake_responses.extract_policy(fake_responses.document_text(p)),
    "extract.invoice": lambda p: fake_responses.extract_invoice(fake_responses.document_text(p)),
    "answer": fake_responses.answer,
    "parse_query": fake_responses.parse_query,
}


def _attachment_text(attachments: Sequence[Attachment]) -> str:
    """Read the text of attached PDFs, as a model with PDF input would.

    Args:
        attachments: Message attachments.

    Returns:
        The text of every PDF page with ``[Página n]`` markers (so the fake
        can report pages); non-PDF attachments are ignored.
    """
    texts = []
    for attachment in attachments:
        if attachment.mime_type == "application/pdf":
            texts.extend(
                f"[Página {number}]\n{text}"
                for number, text in enumerate(read_text_layer(attachment.data), start=1)
            )
    return "\n\n".join(texts)


class FakeLLMProvider:
    """Chat provider that never calls a model.

    By default it answers with deterministic heuristics chosen by ``purpose``.
    Tests can script replies per purpose: each call pops the next scripted
    reply, which makes retry paths easy to reproduce.
    """

    def __init__(self, scripted: Mapping[str, Sequence[str]] | None = None) -> None:
        """Create the provider.

        Args:
            scripted: Optional replies per purpose, returned in order before
                falling back to the default heuristics.
        """
        self._scripted = {k: list(v) for k, v in (scripted or {}).items()}
        self.calls: list[tuple[str, Sequence[ChatMessage]]] = []

    @property
    def model(self) -> str:
        """Name of the fake model."""
        return "fake-llm"

    def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        purpose: str,
        json_mode: bool = False,
    ) -> LLMResponse:
        """Return a deterministic completion.

        Args:
            messages: Conversation; the last user message is used as input.
                If the first user message has a PDF attachment, its text is
                used as the document.
            purpose: Selects the scripted reply or the default heuristic.
            json_mode: Ignored; heuristics already return JSON when needed.

        Returns:
            The fake response, with token counts estimated from word counts.
        """
        self.calls.append((purpose, messages))
        prompt = next((m.content for m in reversed(messages) if m.role == "user"), "")
        attached = next((m.attachments for m in messages if m.attachments), ())
        if attached:
            prompt = f"<documento>\n{_attachment_text(attached)}\n</documento>"
        queue = self._scripted.get(purpose)
        if queue:
            text = queue.pop(0)
        else:
            handler = _DEFAULT_HANDLERS.get(purpose)
            text = handler(prompt) if handler else ""
        return LLMResponse(
            text=text,
            model=self.model,
            input_tokens=sum(len(m.content.split()) for m in messages),
            output_tokens=len(text.split()),
        )


class FakeEmbeddingProvider:
    """Hashing bag-of-words embeddings.

    Texts sharing words get similar vectors, so retrieval behaves sensibly in
    the demo and tests while staying fully deterministic.
    """

    def __init__(self, dimension: int) -> None:
        """Create the provider.

        Args:
            dimension: Vector length (must match the database column).
        """
        self._dimension = dimension

    @property
    def model(self) -> str:
        """Name of the fake model."""
        return "fake-embeddings"

    @property
    def dimension(self) -> int:
        """Configured vector length."""
        return self._dimension

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed texts by hashing their normalized words into buckets.

        Args:
            texts: Texts to embed.

        Returns:
            One L2-normalized vector per text.
        """
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        """Embed one text.

        Args:
            text: Text to embed.

        Returns:
            L2-normalized vector. Texts without words map to a fixed unit
            vector so cosine similarity is always defined.
        """
        vector = [0.0] * self._dimension
        normalized = unicodedata.normalize("NFKD", text.lower())
        ascii_text = normalized.encode("ascii", "ignore").decode()
        for token in _TOKEN.findall(ascii_text):
            if len(token) < 3:
                continue
            digest = hashlib.md5(token.encode(), usedforsecurity=False).digest()
            bucket = int.from_bytes(digest[:4], "big") % self._dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign
        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0:
            vector[0] = 1.0
            return vector
        return [v / norm for v in vector]
