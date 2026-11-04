"""Batch embedding of chunks with dimension checks."""

from collections.abc import Sequence

from app.ai.providers.base import EmbeddingProvider
from app.core.errors import EmbeddingDimensionError


def embed_texts(
    provider: EmbeddingProvider,
    texts: Sequence[str],
    *,
    batch_size: int,
    expected_dim: int,
) -> list[list[float]]:
    """Embed texts in batches and validate every vector's length.

    Args:
        provider: Embedding provider.
        texts: Texts to embed.
        batch_size: Number of texts per provider call.
        expected_dim: Dimension of the database vector column.

    Returns:
        One vector per text, in order.

    Raises:
        EmbeddingDimensionError: If the provider returns a different number of
            vectors or a vector of the wrong length.
    """
    vectors: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        result = provider.embed(batch)
        if len(result) != len(batch):
            raise EmbeddingDimensionError(
                f"Provider returned {len(result)} vectors for {len(batch)} texts"
            )
        for vector in result:
            if len(vector) != expected_dim:
                raise EmbeddingDimensionError(
                    f"Embedding has dimension {len(vector)}; EMBEDDING_DIM is {expected_dim}"
                )
        vectors.extend(result)
    return vectors
