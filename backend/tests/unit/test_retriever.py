import uuid

from app.ai.providers.fake_provider import FakeEmbeddingProvider
from app.ai.rag.retriever import HybridRetriever
from app.domain.dtos import ScoredChunk

DOC = uuid.uuid4()


def _chunk(chunk_id: int, score: float) -> ScoredChunk:
    return ScoredChunk(
        chunk_id=chunk_id, document_id=DOC, filename="p.pdf", page=1, content="x", score=score
    )


class _FakeRepository:
    def __init__(self, vector: list[ScoredChunk], keyword: list[ScoredChunk]) -> None:
        self.vector = vector
        self.keyword = keyword
        self.filters: list[list[uuid.UUID] | None] = []

    def vector_search(self, embedding, limit, document_ids=None, pages=None):
        self.filters.append(document_ids)
        return self.vector[:limit]

    def fulltext_search(self, query, limit, document_ids=None, pages=None):
        self.filters.append(document_ids)
        return self.keyword[:limit]


def _retriever(repo, top_k=5, min_similarity=0.5):
    return HybridRetriever(
        repo,
        FakeEmbeddingProvider(16),
        top_k=top_k,
        candidates=10,
        min_similarity=min_similarity,
        rrf_k=60,
    )


def test_vector_hits_below_threshold_are_discarded():
    repo = _FakeRepository(vector=[_chunk(1, 0.9), _chunk(2, 0.2)], keyword=[])
    result = _retriever(repo).retrieve("pregunta")
    assert [r.chunk.chunk_id for r in result] == [1]
    assert result[0].similarity == 0.9
    assert not result[0].keyword_match


def test_keyword_hit_is_evidence_even_with_low_similarity():
    repo = _FakeRepository(vector=[_chunk(2, 0.1)], keyword=[_chunk(2, 0.05)])
    result = _retriever(repo).retrieve("FS-2024-001")
    assert [r.chunk.chunk_id for r in result] == [2]
    assert result[0].keyword_match
    assert result[0].similarity is None


def test_chunk_found_by_both_searches_ranks_first():
    repo = _FakeRepository(
        vector=[_chunk(1, 0.95), _chunk(2, 0.9)],
        keyword=[_chunk(2, 0.3), _chunk(3, 0.2)],
    )
    result = _retriever(repo).retrieve("pregunta")
    assert result[0].chunk.chunk_id == 2
    assert {r.chunk.chunk_id for r in result} == {1, 2, 3}


def test_results_are_limited_to_top_k():
    repo = _FakeRepository(vector=[_chunk(i, 0.9) for i in range(10)], keyword=[])
    assert len(_retriever(repo, top_k=3).retrieve("pregunta")) == 3


def test_no_hits_means_no_evidence():
    assert _retriever(_FakeRepository(vector=[], keyword=[])).retrieve("pregunta") == []


def test_document_filter_is_passed_to_both_searches():
    repo = _FakeRepository(vector=[], keyword=[])
    _retriever(repo).retrieve("pregunta", [DOC])
    assert repo.filters == [[DOC], [DOC]]


def test_no_filter_searches_every_document():
    repo = _FakeRepository(vector=[], keyword=[])
    _retriever(repo).retrieve("pregunta")
    assert repo.filters == [None, None]


def test_empty_document_list_finds_nothing_without_searching():
    repo = _FakeRepository(vector=[_chunk(1, 0.9)], keyword=[_chunk(1, 0.5)])
    assert _retriever(repo).retrieve("pregunta", []) == []
    assert repo.filters == []
