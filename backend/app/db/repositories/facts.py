"""Repository for the free label-value data of documents (``extracted_fields`` not fixed)."""

import uuid
from collections.abc import Sequence

from sqlalchemy import Select, Text, cast, delete, func, literal_column, select
from sqlalchemy.orm import Session

from app.db.fact_values import from_stored, to_stored
from app.db.models import Document, ExtractedField
from app.db.repositories.chunks import TS_CONFIG
from app.domain.dtos import FactDraft, PageRange, ScoredFact
from app.domain.enums import DocumentType, FieldStatus

_TS_CONFIG = literal_column(f"'{TS_CONFIG}'::regconfig")


class FactRepository:
    """Store, edit and search the free data of documents."""

    def __init__(self, session: Session) -> None:
        """Create the repository.

        Args:
            session: Active SQLAlchemy session.
        """
        self._session = session

    def replace_for_document(
        self,
        document_id: uuid.UUID,
        facts: Sequence[FactDraft],
        embeddings: Sequence[Sequence[float]],
    ) -> int:
        """Replace the free data of a document in the current transaction.

        Args:
            document_id: Owning document.
            facts: New data.
            embeddings: Embedding of each datum, in the same order.

        Returns:
            Number of data stored.
        """
        self._session.execute(
            delete(ExtractedField).where(
                ExtractedField.document_id == document_id, ExtractedField.is_predefined.is_(False)
            )
        )
        self._session.add_all(
            ExtractedField(
                document_id=document_id,
                is_predefined=False,
                label=fact.label,
                value=to_stored(fact.value),
                status=FieldStatus.OK.value,
                page=fact.page,
                table_index=fact.table_index,
                row_index=fact.row_index,
                embedding=list(vector),
            )
            for fact, vector in zip(facts, embeddings, strict=True)
        )
        self._session.flush()
        return len(facts)

    def get(self, document_id: uuid.UUID, fact_id: int) -> ExtractedField | None:
        """Fetch one free datum of a document.

        Args:
            document_id: Owning document.
            fact_id: Datum identifier.

        Returns:
            The datum, or ``None`` if the document has no free datum with that id.
        """
        stmt = select(ExtractedField).where(
            ExtractedField.id == fact_id,
            ExtractedField.document_id == document_id,
            ExtractedField.is_predefined.is_(False),
        )
        return self._session.scalar(stmt)

    def delete(self, fact: ExtractedField) -> None:
        """Delete a free datum in the current transaction.

        Args:
            fact: The datum.
        """
        self._session.delete(fact)
        self._session.flush()

    def vector_search(
        self,
        embedding: Sequence[float],
        limit: int,
        document_ids: Sequence[uuid.UUID] | None = None,
        pages: PageRange | None = None,
    ) -> list[ScoredFact]:
        """Find the free data closest to an embedding by cosine similarity.

        Args:
            embedding: Query embedding.
            limit: Maximum number of results.
            document_ids: Restrict the search to these documents (``None``: all).
            pages: Restrict the search to these pages (``None``: all).

        Returns:
            Data ordered by decreasing similarity, with ``score`` = similarity.
        """
        distance = ExtractedField.embedding.cosine_distance(list(embedding))
        stmt = (
            self._base((1 - distance).label("score"), document_ids, pages)
            .order_by(distance)
            .limit(limit)
        )
        return [_to_scored(row) for row in self._session.execute(stmt)]

    def fulltext_search(
        self,
        query: str,
        limit: int,
        document_ids: Sequence[uuid.UUID] | None = None,
        pages: PageRange | None = None,
        *,
        any_word: bool = False,
    ) -> list[ScoredFact]:
        """Find the free data that share the words of a query.

        Args:
            query: Natural-language query.
            limit: Maximum number of results.
            document_ids: Restrict the search to these documents (``None``: all).
            pages: Restrict the search to these pages (``None``: all).
            any_word: ``True``: one word in common is enough (OR). Used inside a
                single document, so ``monto total`` finds ``TOTAL FACTURA``.
                ``False``: every word must appear (AND), like the chunks; used
                across documents, where OR would match almost every invoice.

        Returns:
            Matching data ordered by decreasing ``ts_rank``.
        """
        ts_query = func.websearch_to_tsquery(_TS_CONFIG, query)
        if any_word:
            ts_query = func.to_tsquery(_TS_CONFIG, func.replace(cast(ts_query, Text), " & ", " | "))
        document = func.to_tsvector(
            _TS_CONFIG, func.concat_ws(" ", ExtractedField.label, cast(ExtractedField.value, Text))
        )
        rank = func.ts_rank(document, ts_query)
        stmt = (
            self._base(rank.label("score"), document_ids, pages)
            .where(document.op("@@")(ts_query))
            .order_by(rank.desc())
            .limit(limit)
        )
        return [_to_scored(row) for row in self._session.execute(stmt)]

    @staticmethod
    def _base(score, document_ids: Sequence[uuid.UUID] | None, pages: PageRange | None) -> Select:
        """Select free data with their document name and a score.

        Args:
            score: Score column of the search.
            document_ids: Documents to search in, or ``None`` for all.
            pages: Inclusive page range, or ``None`` for all pages.

        Returns:
            The query (documents of type ``unknown`` are excluded, like in the chat).
        """
        stmt = (
            select(ExtractedField, Document.filename, score)
            .join(Document, Document.id == ExtractedField.document_id)
            .where(
                ExtractedField.is_predefined.is_(False),
                ExtractedField.embedding.is_not(None),
                Document.document_type.is_distinct_from(DocumentType.UNKNOWN.value),
            )
        )
        if document_ids is not None:
            stmt = stmt.where(ExtractedField.document_id.in_(list(document_ids)))
        if pages is not None and pages.start is not None:
            stmt = stmt.where(ExtractedField.page >= pages.start)
        if pages is not None and pages.end is not None:
            stmt = stmt.where(ExtractedField.page <= pages.end)
        return stmt


def _to_scored(row) -> ScoredFact:
    """Convert a ``(ExtractedField, filename, score)`` row into a ``ScoredFact``.

    Args:
        row: Result row.

    Returns:
        The scored datum.
    """
    fact, filename, score = row
    return ScoredFact(
        fact_id=fact.id,
        document_id=fact.document_id,
        filename=filename,
        page=fact.page,
        label=fact.label,
        value=from_stored(fact.value),
        edited=fact.status == FieldStatus.EDITED.value,
        score=float(score),
    )
