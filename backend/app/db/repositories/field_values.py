"""Repository for ``FieldValue`` rows (the filter index of extracted fields)."""

import uuid
from collections.abc import Sequence

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import FieldValue
from app.domain.dtos import FieldValueDraft


class FieldValueRepository:
    """Store the filter index of a document."""

    def __init__(self, session: Session) -> None:
        """Create the repository.

        Args:
            session: Active SQLAlchemy session.
        """
        self._session = session

    def replace_for_document(
        self, document_id: uuid.UUID, drafts: Sequence[FieldValueDraft]
    ) -> None:
        """Replace every indexed value of a document in the current transaction.

        Args:
            document_id: Owning document.
            drafts: New values.
        """
        self._session.execute(delete(FieldValue).where(FieldValue.document_id == document_id))
        self._session.add_all(
            FieldValue(
                document_id=document_id,
                field_name=d.field_name,
                text_value=d.text_value,
                number_value=d.number_value,
                currency=d.currency,
                date_from=d.date_from,
                date_to=d.date_to,
            )
            for d in drafts
        )
        self._session.flush()

    def replace_for_field(
        self, document_id: uuid.UUID, field_name: str, drafts: Sequence[FieldValueDraft]
    ) -> None:
        """Replace the indexed values of one field in the current transaction.

        Used when the user edits a field, so the chat filters use the new value.

        Args:
            document_id: Owning document.
            field_name: Field whose values are replaced.
            drafts: New values of that field.
        """
        self._session.execute(
            delete(FieldValue).where(
                FieldValue.document_id == document_id, FieldValue.field_name == field_name
            )
        )
        self._session.add_all(
            FieldValue(
                document_id=document_id,
                field_name=d.field_name,
                text_value=d.text_value,
                number_value=d.number_value,
                currency=d.currency,
                date_from=d.date_from,
                date_to=d.date_to,
            )
            for d in drafts
        )
        self._session.flush()
