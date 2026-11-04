"""Repository for ``ExtractedField`` rows."""

import uuid
from collections.abc import Sequence

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import ExtractedField
from app.domain.dtos import FieldDraft


class FieldRepository:
    """Store the structured fields of a document."""

    def __init__(self, session: Session) -> None:
        """Create the repository.

        Args:
            session: Active SQLAlchemy session.
        """
        self._session = session

    def replace_for_document(self, document_id: uuid.UUID, drafts: Sequence[FieldDraft]) -> None:
        """Replace every extracted field of a document in the current transaction.

        Args:
            document_id: Owning document.
            drafts: New fields.
        """
        self._session.execute(
            delete(ExtractedField).where(ExtractedField.document_id == document_id)
        )
        self._session.add_all(
            ExtractedField(
                document_id=document_id,
                name=d.name,
                value=d.value,
                confidence=d.confidence,
                status=d.status,
                error=d.error,
                attempts=d.attempts,
            )
            for d in drafts
        )
        self._session.flush()
