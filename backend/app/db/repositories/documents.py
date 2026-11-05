"""Repository for ``Document`` rows."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Document
from app.domain.enums import DocumentStatus


class DocumentRepository:
    """Read and write documents."""

    def __init__(self, session: Session) -> None:
        """Create the repository.

        Args:
            session: Active SQLAlchemy session.
        """
        self._session = session

    def add(self, document: Document) -> Document:
        """Persist a new document and flush it to obtain its id.

        Args:
            document: The document to insert.

        Returns:
            The same document, now attached to the session.
        """
        self._session.add(document)
        self._session.flush()
        return document

    def get(self, document_id: uuid.UUID, *, with_fields: bool = False) -> Document | None:
        """Fetch a document by id.

        Args:
            document_id: Document identifier.
            with_fields: Whether to eagerly load the known fields and the free
                label-value data.

        Returns:
            The document, or ``None`` when it does not exist.
        """
        stmt = select(Document).where(Document.id == document_id)
        if with_fields:
            stmt = stmt.options(selectinload(Document.fields), selectinload(Document.facts))
        return self._session.scalars(stmt).first()

    def get_by_hash(self, content_hash: str) -> Document | None:
        """Fetch a document by the SHA-256 of its content.

        Args:
            content_hash: Hex SHA-256 digest of the file.

        Returns:
            The matching document, or ``None``.
        """
        return self._session.scalars(
            select(Document).where(Document.content_hash == content_hash)
        ).first()

    def list(self, limit: int = 100, offset: int = 0) -> list[Document]:
        """List documents, newest first.

        Args:
            limit: Maximum number of rows.
            offset: Number of rows to skip.

        Returns:
            The requested page of documents.
        """
        stmt = select(Document).order_by(Document.created_at.desc()).limit(limit).offset(offset)
        return list(self._session.scalars(stmt))

    def set_status(
        self,
        document: Document,
        status: DocumentStatus,
        *,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Update the processing status and error of a document.

        Args:
            document: The document to update.
            status: New status.
            error_code: Machine-readable error code, or ``None`` to clear it.
            error_message: Human-readable error, or ``None`` to clear it.
        """
        document.status = status
        document.error_code = error_code
        document.error_message = error_message
        self._session.flush()
