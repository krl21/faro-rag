"""Local embeddings with sentence-transformers (no API key required)."""

import threading
from collections.abc import Sequence
from typing import Any

from app.core.errors import ProviderError


class SentenceTransformersEmbeddingProvider:
    """Embeddings computed in-process with a sentence-transformers model.

    The model is loaded lazily on first use and shared by every thread.
    ``sentence-transformers`` is an optional dependency (extra
    ``local-embeddings``), so it is imported only when this provider is used.
    """

    def __init__(self, model: str, *, batch_size: int = 32) -> None:
        """Create the provider.

        Args:
            model: Hugging Face model name.
            batch_size: Number of texts encoded per forward pass.
        """
        self._model_name = model
        self._batch_size = batch_size
        self._model: Any | None = None
        self._lock = threading.Lock()

    @property
    def model(self) -> str:
        """Name of the embedding model."""
        return self._model_name

    @property
    def dimension(self) -> int:
        """Vector length reported by the loaded model."""
        model = self._load()
        # Renamed in sentence-transformers 6; keep the old name for older versions.
        getter = getattr(model, "get_embedding_dimension", None) or (
            model.get_sentence_embedding_dimension
        )
        return int(getter())

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed a batch of texts locally.

        Vectors are L2-normalized, so cosine similarity equals the dot product.

        Args:
            texts: Texts to embed.

        Returns:
            One vector per input text.

        Raises:
            ProviderError: If the model cannot be loaded or encoding fails.
        """
        try:
            vectors = self._load().encode(
                list(texts),
                batch_size=self._batch_size,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f"Local embedding failed: {exc}") from exc
        return [vector.tolist() for vector in vectors]

    def _load(self) -> Any:
        """Load the model once (thread-safe).

        Returns:
            The ``SentenceTransformer`` instance.

        Raises:
            ProviderError: If the library is missing or the model cannot be loaded.
        """
        if self._model is None:
            with self._lock:
                if self._model is None:
                    try:
                        from sentence_transformers import SentenceTransformer
                    except ImportError as exc:
                        raise ProviderError(
                            "sentence-transformers is not installed "
                            "(install the 'local-embeddings' extra)"
                        ) from exc
                    try:
                        self._model = SentenceTransformer(self._model_name, device="cpu")
                    except Exception as exc:
                        raise ProviderError(
                            f"Cannot load embedding model {self._model_name}: {exc}"
                        ) from exc
        return self._model
