"""Hybrid retrieval: vector search + full-text search fused with RRF."""

import logging
import uuid
from collections.abc import Sequence

from app.ai.providers.base import EmbeddingProvider
from app.core.flow_logging import fields
from app.db.repositories import ChunkRepository
from app.domain.dtos import PageRange, RetrievedChunk, ScoredChunk

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Combine pgvector similarity and PostgreSQL full-text search.

    Both searches return ranked candidates that are merged with Reciprocal
    Rank Fusion (RRF), which needs no score normalization. A chunk counts as
    evidence only if its vector similarity reaches ``min_similarity`` or it
    matches the full-text query; everything else is discarded.
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
    ) -> None:
        """Create the retriever.

        Args:
            repository: Chunk repository.
            embeddings: Provider used to embed the question.
            top_k: Maximum chunks returned.
            candidates: Candidates fetched from each search before fusion.
            min_similarity: Minimum cosine similarity for a vector-only match.
            rrf_k: RRF constant (higher values flatten rank differences).
        """
        self._repository = repository
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
        if document_ids is not None and not document_ids:
            return []  # The filters matched no document: nothing to embed or search.
        query_vector = self._embeddings.embed([question])[0]
        
        print(f"---> query_vector: {query_vector[:5]}...")
        print(f"---> self._candidates: {self._candidates}")
        print(f"---> document_ids: {document_ids}")
        print(f"---> pages: {pages}")
        
        
        vector_hits = self._repository.vector_search(
            query_vector, self._candidates, document_ids, pages
        )
        print(f'---> len(vector_hits): {len(vector_hits)}')
        
        keyword_hits = self._repository.fulltext_search(
            question, self._candidates, document_ids, pages
        )
        print(f'---> len(keyword_hits): {len(keyword_hits)}')
        print(f'---> keyword_hits: {keyword_hits}')

        fused: dict[int, float] = {}
        similarity: dict[int, float] = {}
        chunks: dict[int, ScoredChunk] = {}
        for rank, hit in enumerate(vector_hits, start=1):
            if hit.score < self._min_similarity:
                continue
            fused[hit.chunk_id] = fused.get(hit.chunk_id, 0.0) + 1 / (self._rrf_k + rank)
            similarity[hit.chunk_id] = hit.score
            chunks[hit.chunk_id] = hit
        keyword_ids = set()
        for rank, hit in enumerate(keyword_hits, start=1):
            fused[hit.chunk_id] = fused.get(hit.chunk_id, 0.0) + 1 / (self._rrf_k + rank)
            keyword_ids.add(hit.chunk_id)
            chunks.setdefault(hit.chunk_id, hit)

        ranked = sorted(fused.items(), key=lambda item: item[1], reverse=True)[: self._top_k]
        logger.info(
            "fragments retrieved",
            extra=fields(
                vector_hits=len(vector_hits),
                vector_hits_above_threshold=len(similarity),
                keyword_hits=len(keyword_hits),
                selected=len(ranked),
                document_filter=None if document_ids is None else len(document_ids),
            ),
        )
        logger.debug(
            "selected fragments",
            extra=fields(
                search_text=question,
                fragments=[
                    {
                        "chunk_id": chunk_id,
                        "document_id": str(chunks[chunk_id].document_id),
                        "page": chunks[chunk_id].page,
                        "similarity": similarity.get(chunk_id),
                        "keyword_match": chunk_id in keyword_ids,
                        "fused_score": round(score, 5),
                    }
                    for chunk_id, score in ranked
                ],
            ),
        )
        return [
            RetrievedChunk(
                chunk=chunks[chunk_id],
                similarity=similarity.get(chunk_id),
                keyword_match=chunk_id in keyword_ids,
                fused_score=score,
            )
            for chunk_id, score in ranked
        ]
