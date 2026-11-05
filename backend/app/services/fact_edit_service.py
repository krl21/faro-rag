"""Use case: the user corrects or deletes a free label-value datum of a document."""

import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.ai.ingestion.fact_parsing import MAX_LABEL_CHARS, MAX_VALUE_CHARS, describe
from app.ai.providers.base import EmbeddingProvider
from app.core.errors import (
    DocumentNotFoundError,
    DocumentNotReadyError,
    FactNotFoundError,
    InvalidFactValueError,
)
from app.core.flow_logging import fields
from app.core.telemetry import get_tracer
from app.db.fact_values import from_stored, to_stored
from app.db.models import ExtractedField
from app.db.repositories import DocumentRepository, FactRepository
from app.domain.enums import DocumentStatus, FieldStatus

logger = logging.getLogger(__name__)

# Most columns a table row may have after an edit.
_MAX_COLUMNS = 30


class FactEditService:
    """Edit or delete the free data of a document, keeping the chat search in sync."""

    def __init__(
        self,
        session: Session,
        embeddings: EmbeddingProvider,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Create the service.

        Args:
            session: Request session.
            embeddings: Provider used to embed the edited datum again.
            clock: Current time (injectable for tests).
        """
        self._session = session
        self._documents = DocumentRepository(session)
        self._facts = FactRepository(session)
        self._embeddings = embeddings
        self._clock = clock

    def edit(
        self,
        document_id: uuid.UUID,
        fact_id: int,
        *,
        label: str | None = None,
        value: str | dict[str, str] | None = None,
    ) -> ExtractedField:
        """Replace the label and/or the value of a free datum.

        The datum found in the document is kept in ``original_value`` the
        first time (``{"label": ..., "value": ...}``), and its embedding is
        computed again so the chat finds it by its new text.

        Args:
            document_id: Document identifier.
            fact_id: Datum identifier.
            label: New label (``None`` keeps the current one).
            value: New value: a string, or the columns of a table row
                (``None`` keeps the current one).

        Returns:
            The updated datum.

        Raises:
            DocumentNotFoundError: If the document does not exist.
            DocumentNotReadyError: If the document is not ``done``.
            FactNotFoundError: If the document has no free datum with that id.
            InvalidFactValueError: If the label or the value is empty or too long.
        """
        with get_tracer().start_as_current_span("facts.edit") as span:
            span.set_attribute("document.id", str(document_id))
            span.set_attribute("fact.id", fact_id)
            fact = self._fact(document_id, fact_id)
            new_label = fact.label if label is None else _valid_label(label)
            new_value = from_stored(fact.value) if value is None else _valid_value(value)

            first_edit = fact.status != FieldStatus.EDITED
            if first_edit:
                fact.original_value = {"label": fact.label, "value": fact.value}
            fact.label = new_label
            fact.value = to_stored(new_value)
            fact.status = FieldStatus.EDITED
            fact.edited_at = self._clock()
            fact.embedding = list(self._embeddings.embed([describe(new_label, new_value)])[0])
            self._session.commit()
            self._session.refresh(fact)
            logger.info(
                "document datum edited by the user",
                extra=fields(document_id=str(document_id), fact_id=fact_id, first_edit=first_edit),
            )
            logger.debug(
                "document datum edit values",
                extra=fields(
                    document_id=str(document_id),
                    fact_id=fact_id,
                    original_value=fact.original_value,
                    label=new_label,
                    value=new_value,
                ),
            )
            return fact

    def delete(self, document_id: uuid.UUID, fact_id: int) -> None:
        """Delete a free datum (the chat stops using it).

        Reprocessing the document extracts its data again, this one included.

        Args:
            document_id: Document identifier.
            fact_id: Datum identifier.

        Raises:
            DocumentNotFoundError: If the document does not exist.
            DocumentNotReadyError: If the document is not ``done``.
            FactNotFoundError: If the document has no free datum with that id.
        """
        with get_tracer().start_as_current_span("facts.delete") as span:
            span.set_attribute("document.id", str(document_id))
            span.set_attribute("fact.id", fact_id)
            fact = self._fact(document_id, fact_id)
            self._facts.delete(fact)
            self._session.commit()
            logger.info(
                "document datum deleted by the user",
                extra=fields(document_id=str(document_id), fact_id=fact_id),
            )

    def _fact(self, document_id: uuid.UUID, fact_id: int) -> ExtractedField:
        """Fetch a free datum of a processed document.

        Args:
            document_id: Document identifier.
            fact_id: Datum identifier.

        Returns:
            The datum.

        Raises:
            DocumentNotFoundError: If the document does not exist.
            DocumentNotReadyError: If the document is not ``done``.
            FactNotFoundError: If the document has no free datum with that id.
        """
        document = self._documents.get(document_id)
        if document is None:
            raise DocumentNotFoundError(f"Document {document_id} not found")
        if document.status != DocumentStatus.DONE:
            raise DocumentNotReadyError(
                f"Document {document_id} is {document.status}; its data can only be "
                "changed once it is processed"
            )
        fact = self._facts.get(document_id, fact_id)
        if fact is None:
            raise FactNotFoundError(f"Document {document_id} has no datum {fact_id}")
        return fact


def _valid_label(label: str) -> str:
    """Check a label typed by the user.

    Args:
        label: New label.

    Returns:
        The label without surrounding spaces.

    Raises:
        InvalidFactValueError: If it is empty or too long.
    """
    label = label.strip()
    if not label:
        raise InvalidFactValueError("The label cannot be empty")
    if len(label) > MAX_LABEL_CHARS:
        raise InvalidFactValueError(f"The label is longer than {MAX_LABEL_CHARS} characters")
    return label


def _valid_value(value: str | dict[str, str]) -> str | dict[str, str]:
    """Check a value typed by the user: a text or the columns of a table row.

    Args:
        value: New value.

    Returns:
        The value without surrounding spaces (empty columns removed).

    Raises:
        InvalidFactValueError: If it is empty or too long.
    """
    if isinstance(value, str):
        value = value.strip()
        if not value:
            raise InvalidFactValueError("The value cannot be empty")
        if len(value) > MAX_VALUE_CHARS:
            raise InvalidFactValueError(f"The value is longer than {MAX_VALUE_CHARS} characters")
        return value
    columns = {k.strip(): v.strip() for k, v in value.items() if k.strip() and v.strip()}
    if not columns:
        raise InvalidFactValueError("A table row needs at least one column with a value")
    if len(columns) > _MAX_COLUMNS:
        raise InvalidFactValueError(f"A table row can have at most {_MAX_COLUMNS} columns")
    too_long = [
        k for k, v in columns.items() if len(k) > MAX_LABEL_CHARS or len(v) > MAX_VALUE_CHARS
    ]
    if too_long:
        raise InvalidFactValueError(f"Column {too_long[0]!r} or its value is too long")
    return columns
