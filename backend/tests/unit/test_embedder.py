import pytest

from app.ai.ingestion.embedder import embed_texts
from app.ai.providers.fake_provider import FakeEmbeddingProvider
from app.core.errors import EmbeddingDimensionError


class _CountingProvider(FakeEmbeddingProvider):
    def __init__(self, dimension: int) -> None:
        super().__init__(dimension)
        self.batches: list[int] = []

    def embed(self, texts):
        self.batches.append(len(texts))
        return super().embed(texts)


class _BrokenProvider(FakeEmbeddingProvider):
    def embed(self, texts):
        return super().embed(texts)[:-1]


def test_texts_are_embedded_in_batches():
    provider = _CountingProvider(dimension=16)
    vectors = embed_texts(provider, [f"t{i}" for i in range(7)], batch_size=3, expected_dim=16)
    assert len(vectors) == 7
    assert provider.batches == [3, 3, 1]


def test_no_texts_means_no_calls():
    provider = _CountingProvider(dimension=16)
    assert embed_texts(provider, [], batch_size=3, expected_dim=16) == []
    assert provider.batches == []


def test_wrong_dimension_is_rejected():
    with pytest.raises(EmbeddingDimensionError, match="EMBEDDING_DIM is 32"):
        embed_texts(FakeEmbeddingProvider(16), ["a"], batch_size=3, expected_dim=32)


def test_missing_vectors_are_rejected():
    with pytest.raises(EmbeddingDimensionError, match="vectors for"):
        embed_texts(_BrokenProvider(16), ["a", "b"], batch_size=5, expected_dim=16)
