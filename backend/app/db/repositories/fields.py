"""Repository for ``ExtractedField`` rows."""

import dataclasses
import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import delete, select
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
                page=d.page,
                **_filter_columns(d),
            )
            for d in drafts
        )
        self._session.flush()

    def get(self, document_id: uuid.UUID, name: str) -> ExtractedField | None:
        """Fetch one field of a document.

        Args:
            document_id: Owning document.
            name: Field name.

        Returns:
            The field, or ``None`` if the document has no field with that name.
        """
        stmt = select(ExtractedField).where(
            ExtractedField.document_id == document_id, ExtractedField.name == name
        )
        return self._session.scalar(stmt)


def _filter_columns(draft: FieldDraft) -> dict[str, Any]:
    """Return the filter columns of a draft as model keyword arguments.

    Args:
        draft: Field to store.

    Returns:
        The typed columns, or an empty dict when the field has none.
    """
    return dataclasses.asdict(draft.filter_columns) if draft.filter_columns else {}
