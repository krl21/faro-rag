"""Repository for ``Chunk`` rows: idempotent writes and hybrid search queries."""

import uuid
from collections.abc import Sequence

from sqlalchemy import delete, func, literal_column, select, text
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document
from app.domain.dtos import ChunkDraft, ScoredChunk

# Same text search configuration used by the generated ``tsv`` column.
TS_CONFIG = "spanish"


class ChunkRepository:
    """Store and search document chunks."""

    def __init__(self, session: Session) -> None:
        """Create the repository.

        Args:
            session: Active SQLAlchemy session.
        """
        self._session = session

    def replace_for_document(self, document_id: uuid.UUID, drafts: Sequence[ChunkDraft]) -> int:
        """Replace every chunk of a document in the current transaction.

        Deleting and inserting inside one transaction makes reprocessing
        idempotent: a retry never duplicates chunks, and a crash before commit
        leaves the previous chunks untouched.

        Args:
            document_id: Owning document.
            drafts: New chunks.

        Returns:
            Number of chunks inserted.
        """
        self._session.execute(delete(Chunk).where(Chunk.document_id == document_id))
        self._session.add_all(
            Chunk(
                document_id=document_id,
                page=d.page,
                chunk_index=d.chunk_index,
                content=d.content,
                embedding=list(d.embedding),
            )
            for d in drafts
        )
        self._session.flush()
        return len(drafts)

    def count_for_document(self, document_id: uuid.UUID) -> int:
        """Count the chunks of a document.

        Args:
            document_id: Owning document.

        Returns:
            Number of chunks.
        """
        stmt = select(func.count()).select_from(Chunk).where(Chunk.document_id == document_id)
        return self._session.scalar(stmt) or 0

    def vector_search(
        self,
        embedding: Sequence[float],
        limit: int,
        document_ids: Sequence[uuid.UUID] | None = None,
    ) -> list[ScoredChunk]:
        """Find the chunks closest to an embedding by cosine similarity.

        Args:
            embedding: Query embedding.
            limit: Maximum number of results.
            document_ids: Restrict the search to these documents (``None``: all).

        Returns:
            Chunks ordered by decreasing similarity.
        """
        distance = Chunk.embedding.cosine_distance(list(embedding))
        stmt = (
            select(Chunk, Document.filename, (1 - distance).label("score"))
            .join(Document, Document.id == Chunk.document_id)
            .order_by(distance)
            .limit(limit)
        )
        if document_ids is not None:
            stmt = stmt.where(Chunk.document_id.in_(list(document_ids)))
        return [self._to_scored(row) for row in self._session.execute(stmt)]

    def fulltext_search(
        self,
        query: str,
        limit: int,
        document_ids: Sequence[uuid.UUID] | None = None,
    ) -> list[ScoredChunk]:
        """Find chunks matching a query with PostgreSQL full-text search.

        Uses ``websearch_to_tsquery`` so user input never breaks the query syntax.

        Args:
            query: Natural-language query.
            limit: Maximum number of results.
            document_ids: Restrict the search to these documents (``None``: all).

        Returns:
            Matching chunks ordered by decreasing ``ts_rank``.
        """
        ts_query = func.websearch_to_tsquery(literal_column(f"'{TS_CONFIG}'::regconfig"), query)
        rank = func.ts_rank(Chunk.tsv, ts_query)
        stmt = (
            select(Chunk, Document.filename, rank.label("score"))
            .join(Document, Document.id == Chunk.document_id)
            .where(Chunk.tsv.op("@@")(ts_query))
            .order_by(rank.desc())
            .limit(limit)
        )
        if document_ids is not None:
            stmt = stmt.where(Chunk.document_id.in_(list(document_ids)))
        return [self._to_scored(row) for row in self._session.execute(stmt)]

    def embedding_column_dimension(self) -> int | None:
        """Read the dimension of the ``chunks.embedding`` column from the catalog.

        Returns:
            The declared vector dimension, or ``None`` if the table does not exist.
        """
        stmt = text(
            "SELECT atttypmod FROM pg_attribute "
            "WHERE attrelid = to_regclass('chunks') AND attname = 'embedding'"
        )
        return self._session.scalar(stmt)

    @staticmethod
    def _to_scored(row) -> ScoredChunk:
        """Convert a ``(Chunk, filename, score)`` row into a ``ScoredChunk``.

        Args:
            row: Result row.

        Returns:
            The scored chunk.
        """
        chunk, filename, score = row
        return ScoredChunk(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            filename=filename,
            page=chunk.page,
            content=chunk.content,
            score=float(score),
        )
