"""Pick the free label-value data of a document that are relevant to a question."""

import logging
import uuid

from app.ai.ingestion.fact_parsing import describe
from app.ai.providers.base import EmbeddingProvider
from app.core.flow_logging import fields
from app.db.repositories import FactRepository
from app.domain.dtos import FieldFact, PageRange, ScoredFact

logger = logging.getLogger(__name__)


class FactRetriever:
    """Rank the free data of one document by vector similarity and shared words.

    Used by the questions about one document. Both rankings are merged with
    Reciprocal Rank Fusion, like the chunks. There is no similarity threshold
    and one word in common is enough: the data are short, the search runs over
    a single document and the LLM decides which ones answer the question. Only
    the ``top_k`` best are sent, to keep the prompt small.
    """

    def __init__(
        self,
        repository: FactRepository,
        embeddings: EmbeddingProvider,
        *,
        top_k: int,
        rrf_k: int,
    ) -> None:
        """Create the retriever.

        Args:
            repository: Free data repository.
            embeddings: Provider used to embed the question.
            top_k: Maximum data returned (``RETRIEVAL_FACTS_TOP_K``).
            rrf_k: RRF constant.
        """
        self._repository = repository
        self._embeddings = embeddings
        self._top_k = top_k
        self._rrf_k = rrf_k

    def retrieve(
        self,
        document_id: uuid.UUID,
        question: str,
        pages: PageRange | None = None,
    ) -> list[FieldFact]:
        """Find the data of a document that best match a question.

        Args:
            document_id: Document asked about.
            question: User question.
            pages: Restrict the data to these pages (``None``: all).

        Returns:
            Up to ``top_k`` data as citable facts, best first.
        """
        if self._top_k == 0:
            return []
        candidates = self._top_k * 2
        vector = self._embeddings.embed([question])[0]
        by_vector = self._repository.vector_search(vector, candidates, [document_id], pages)
        by_words = self._repository.fulltext_search(
            question, candidates, [document_id], pages, any_word=True
        )

        scores: dict[int, float] = {}
        found: dict[int, ScoredFact] = {}
        for ranking in (by_vector, by_words):
            for rank, fact in enumerate(ranking, start=1):
                scores[fact.fact_id] = scores.get(fact.fact_id, 0.0) + 1 / (self._rrf_k + rank)
                found[fact.fact_id] = fact
        best = sorted(scores, key=scores.__getitem__, reverse=True)[: self._top_k]
        logger.info(
            "document data retrieved",
            extra=fields(
                document_id=str(document_id),
                vector_hits=len(by_vector),
                keyword_hits=len(by_words),
                selected=len(best),
            ),
        )
        return [to_field_fact(found[fact_id]) for fact_id in best]


def to_field_fact(fact: ScoredFact) -> FieldFact:
    """Turn a found free datum into a citable fact.

    Args:
        fact: The datum.

    Returns:
        The fact. A table row is labelled with its first cell and shows its
        other columns as the value (``Kit: Cantidad: 1 ud; Importe: 1.280,00 €``).
    """
    if isinstance(fact.value, dict):
        shown = describe(fact.label, {k: v for k, v in fact.value.items() if v != fact.label})
    else:
        shown = fact.value
    return FieldFact(
        document_id=fact.document_id,
        filename=fact.filename,
        page=fact.page,
        name=None,
        label=fact.label,
        value=shown,
        edited=fact.edited,
    )
