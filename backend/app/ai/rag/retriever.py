"""Hybrid retrieval: vector search + full-text search fused with RRF."""

import logging
import uuid
from collections.abc import Sequence

from app.ai.providers.base import EmbeddingProvider
from app.ai.rag.fact_retriever import to_field_fact
from app.core.flow_logging import fields
from app.db.repositories import ChunkRepository, FactRepository
from app.domain.dtos import FieldFact, PageRange, RetrievedChunk, ScoredChunk, ScoredFact

logger = logging.getLogger(__name__)

# Key of a candidate in the fused ranking: ("chunk", id) or ("fact", id).
_Key = tuple[str, int]


class HybridRetriever:
    """Combine pgvector similarity and PostgreSQL full-text search.

    Both searches return ranked candidates that are merged with Reciprocal
    Rank Fusion (RRF), which needs no score normalization. A candidate counts
    as evidence only if its vector similarity reaches ``min_similarity`` or it
    matches the full-text query (every word); everything else is discarded.

    With a ``FactRepository``, ``retrieve_sources`` also searches the free
    label-value data of the documents (tables and "campo: valor" lines): they
    compete with the chunks in the same ranking, under the same evidence
    rules, for the same ``top_k`` places.
    """

    def __init__(
        self,
        repository: ChunkRepository,
        embeddings: EmbeddingProvider,
        *,
        top_k: int,
        candidates: int,
        min_similarity: float,
        rrf_k: int,
        facts: FactRepository | None = None,
    ) -> None:
        """Create the retriever.

        Args:
            repository: Chunk repository.
            embeddings: Provider used to embed the question.
            top_k: Maximum sources returned.
            candidates: Candidates fetched from each search before fusion.
            min_similarity: Minimum cosine similarity for a vector-only match.
            rrf_k: RRF constant (higher values flatten rank differences).
            facts: Free data repository, used by ``retrieve_sources``.
        """
        self._repository = repository
        self._facts = facts
        self._embeddings = embeddings
        self._top_k = top_k
        self._candidates = candidates
        self._min_similarity = min_similarity
        self._rrf_k = rrf_k

    def retrieve(
        self,
        question: str,
        document_ids: Sequence[uuid.UUID] | None = None,
        pages: PageRange | None = None,
    ) -> list[RetrievedChunk]:
        """Find the chunks that best support an answer to the question.

        Args:
            question: Text to search for (the question, or its part left after
                removing the filters).
            document_ids: Restrict the search to these documents; ``None``
                searches every document and an empty list finds nothing.
            pages: Restrict the search to these pages (``None``: all).

        Returns:
            Up to ``top_k`` relevant chunks, best first. Empty when nothing
            passes the relevance criteria (no evidence).
        """
        chunks, _ = self._search(question, document_ids, pages, with_facts=False)
        return chunks

    def retrieve_sources(
        self,
        question: str,
        document_ids: Sequence[uuid.UUID] | None = None,
        pages: PageRange | None = None,
    ) -> tuple[list[RetrievedChunk], list[FieldFact]]:
        """Find the chunks and free data that best support an answer.

        Chunks and free data share one ranking and the ``top_k`` places: a
        short datum such as ``TOTAL FACTURA: 40.492,65 €`` can take the place
        of a long chunk when it matches the question better.

        Args:
            question: Text to search for.
            document_ids: Restrict the search to these documents; ``None``
                searches every document and an empty list finds nothing.
            pages: Restrict the search to these pages (``None``: all).

        Returns:
            The chunks and the data selected, each list best first.
        """
        return self._search(question, document_ids, pages, with_facts=self._facts is not None)

    def _search(
        self,
        question: str,
        document_ids: Sequence[uuid.UUID] | None,
        pages: PageRange | None,
        *,
        with_facts: bool,
    ) -> tuple[list[RetrievedChunk], list[FieldFact]]:
        """Run the searches, fuse them and keep the best ``top_k`` candidates.

        Args:
            question: Text to search for.
            document_ids: Documents to search in (``None``: all).
            pages: Pages to search in (``None``: all).
            with_facts: Whether the free data compete with the chunks.

        Returns:
            The selected chunks and data.
        """
        if document_ids is not None and not document_ids:
            return [], []  # The filters matched no document: nothing to embed or search.
        query_vector = self._embeddings.embed([question])[0]
        rankings: list[tuple[str, Sequence[ScoredChunk | ScoredFact], bool]] = [
            (
                "chunk",
                self._repository.vector_search(query_vector, self._candidates, document_ids, pages),
                True,
            ),
            (
                "chunk",
                self._repository.fulltext_search(question, self._candidates, document_ids, pages),
                False,
            ),
        ]
        if with_facts and self._facts is not None:
            rankings += [
                (
                    "fact",
                    self._facts.vector_search(query_vector, self._candidates, document_ids, pages),
                    True,
                ),
                (
                    "fact",
                    self._facts.fulltext_search(question, self._candidates, document_ids, pages),
                    False,
                ),
            ]

        fused: dict[_Key, float] = {}
        similarity: dict[_Key, float] = {}
        keyword: set[_Key] = set()
        found: dict[_Key, ScoredChunk | ScoredFact] = {}
        for kind, hits, is_vector in rankings:
            for rank, hit in enumerate(hits, start=1):
                key = (kind, hit.chunk_id if kind == "chunk" else hit.fact_id)
                if is_vector:
                    if hit.score < self._min_similarity:
                        continue
                    similarity[key] = hit.score
                else:
                    keyword.add(key)
                fused[key] = fused.get(key, 0.0) + 1 / (self._rrf_k + rank)
                found.setdefault(key, hit)

        ranked = sorted(fused.items(), key=lambda item: item[1], reverse=True)[: self._top_k]
        chunks = [
            RetrievedChunk(
                chunk=found[key],
                similarity=similarity.get(key),
                keyword_match=key in keyword,
                fused_score=score,
            )
            for key, score in ranked
            if key[0] == "chunk"
        ]
        facts = [to_field_fact(found[key]) for key, _ in ranked if key[0] == "fact"]
        logger.info(
            "fragments retrieved",
            extra=fields(
                **{
                    f"{kind}_{'vector' if is_vector else 'keyword'}_hits": len(hits)
                    for kind, hits, is_vector in rankings
                },
                above_threshold=len(similarity),
                selected_chunks=len(chunks),
                selected_facts=len(facts),
                document_filter=None if document_ids is None else len(document_ids),
            ),
        )
        logger.debug(
            "selected sources",
            extra=fields(
                search_text=question,
                sources=[
                    {
                        "kind": key[0],
                        "id": key[1],
                        "document_id": str(found[key].document_id),
                        "page": found[key].page,
                        "similarity": similarity.get(key),
                        "keyword_match": key in keyword,
                        "fused_score": round(score, 5),
                    }
                    for key, score in ranked
                ],
            ),
        )
        return chunks, facts
