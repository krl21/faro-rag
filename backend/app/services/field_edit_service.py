"""Use case: the user sets or corrects the value of an extracted field."""

import dataclasses
import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.extraction.field_indexing import filter_columns
from app.ai.extraction.field_validation import format_errors
from app.ai.extraction.specs import FieldSpec, find_spec
from app.core.errors import (
    DocumentNotFoundError,
    DocumentNotReadyError,
    FieldNotFoundError,
    InvalidFieldValueError,
)
from app.core.flow_logging import fields
from app.core.telemetry import get_tracer
from app.db.models import ExtractedField
from app.db.repositories import DocumentRepository, FieldRepository
from app.domain.dtos import FieldDraft
from app.domain.enums import DocumentStatus, FieldStatus

logger = logging.getLogger(__name__)


class FieldEditService:
    """Validate, store and reindex a value typed by the user."""

    def __init__(
        self, session: Session, clock: Callable[[], datetime] = lambda: datetime.now(UTC)
    ) -> None:
        """Create the service.

        Args:
            session: Request session.
            clock: Current time (injectable for tests).
        """
        self._session = session
        self._documents = DocumentRepository(session)
        self._fields = FieldRepository(session)
        self._clock = clock

    def edit(self, document_id: uuid.UUID, name: str, value: Any) -> tuple[ExtractedField, str]:
        """Replace the value of a field with one given by the user.

        Works for any field of the document type, including ``not_found`` and
        ``failed`` ones (the user fills in the missing value). The value is
        validated with the same Pydantic type as the LLM output. The LLM value
        is kept in ``original_value`` the first time, and the chat filter index
        columns of that field are refreshed in the same transaction.

        Args:
            document_id: Document identifier.
            name: Field name (for example ``policy_number``).
            value: New value, in the shape the API returns (string, ISO date,
                ``{start, end}``, ``{amount, currency}`` or list of strings).

        Returns:
            The updated field and the document type.

        Raises:
            DocumentNotFoundError: If the document does not exist.
            DocumentNotReadyError: If the document is not ``done``.
            FieldNotFoundError: If the document type has no such field.
            InvalidFieldValueError: If the value does not have the expected shape.
        """
        with get_tracer().start_as_current_span("fields.edit") as span:
            span.set_attribute("document.id", str(document_id))
            span.set_attribute("field.name", name)
            document = self._documents.get(document_id)
            if document is None:
                raise DocumentNotFoundError(f"Document {document_id} not found")
            if document.status != DocumentStatus.DONE:
                raise DocumentNotReadyError(
                    f"Document {document_id} is {document.status}; fields can only be "
                    "edited once it is processed"
                )
            spec = find_spec(document.document_type, name)
            if spec is None:
                raise FieldNotFoundError(
                    f"Field {name!r} does not exist for {document.document_type} documents"
                )
            new_value = self._validated(spec, value)

            field = self._fields.get(document_id, name) or self._new_field(document_id, name)
            previous_status = field.status
            if field.status != FieldStatus.EDITED:
                field.original_value = field.value  # Keep the LLM value once.
            field.value = new_value
            field.status = FieldStatus.EDITED
            field.confidence = None  # The LLM confidence no longer applies.
            field.error = None
            field.edited_at = self._clock()

            draft = FieldDraft(
                name=name,
                value=new_value,
                confidence=None,
                status=FieldStatus.EDITED,
                error=None,
                attempts=field.attempts,
            )
            # Refresh the filter columns of the same row, so the chat filters use the new value.
            columns = filter_columns(draft)
            if columns is None:
                field.set_filter_columns()
            else:
                field.set_filter_columns(**dataclasses.asdict(columns))
            self._session.commit()
            self._session.refresh(field)
            logger.info(
                "field edited by the user",
                extra=fields(
                    document_id=str(document_id),
                    field=name,
                    value_type=spec.value_type.value,
                    first_edit=previous_status != FieldStatus.EDITED,
                ),
            )
            logger.debug(
                "field edit values",
                extra=fields(
                    document_id=str(document_id),
                    field=name,
                    original_value=field.original_value,
                    new_value=new_value,
                ),
            )
            return field, document.document_type

    def delete(self, document_id: uuid.UUID, name: str) -> None:
        """Delete a fixed field of a document.

        The row is removed: the field disappears from the field list and the
        chat filters and answers stop using it. ``PATCH`` can fill it in again
        later. Reprocessing the document extracts it again. ``document_type``
        can be neither edited nor deleted (it decides which fields apply).

        Args:
            document_id: Document identifier.
            name: Field name (for example ``policy_number``).

        Raises:
            DocumentNotFoundError: If the document does not exist.
            DocumentNotReadyError: If the document is not ``done``.
            FieldNotFoundError: If the document has no field with that name, or
                it is ``document_type``.
        """
        with get_tracer().start_as_current_span("fields.delete") as span:
            span.set_attribute("document.id", str(document_id))
            span.set_attribute("field.name", name)
            document = self._documents.get(document_id)
            if document is None:
                raise DocumentNotFoundError(f"Document {document_id} not found")
            if document.status != DocumentStatus.DONE:
                raise DocumentNotReadyError(
                    f"Document {document_id} is {document.status}; fields can only be "
                    "deleted once it is processed"
                )
            field = self._fields.get(document_id, name)
            # Same rule as PATCH: only the fields of the document type (not document_type).
            if field is None or find_spec(document.document_type, name) is None:
                raise FieldNotFoundError(f"Document {document_id} has no deletable field {name!r}")
            self._fields.delete(field)
            self._session.commit()
            logger.info(
                "field deleted by the user", extra=fields(document_id=str(document_id), field=name)
            )

    @staticmethod
    def _validated(spec: FieldSpec, value: Any) -> Any:
        """Validate a user value and return it in its JSON form.

        Args:
            spec: Field definition.
            value: Raw value from the request.

        Returns:
            The normalized JSON value (for example, the currency in upper case).

        Raises:
            InvalidFieldValueError: If the value is empty or has the wrong shape.
        """
        if value is None or value == [] or (isinstance(value, str) and not value.strip()):
            raise InvalidFieldValueError(f"A value is required for {spec.name!r}")
        try:
            validated = spec.value_adapter.validate_python(value)
        except ValidationError as exc:
            raise InvalidFieldValueError(
                f"Invalid value for {spec.name!r}: {format_errors(exc)}"
            ) from exc
        return spec.value_adapter.dump_python(validated, mode="json")

    def _new_field(self, document_id: uuid.UUID, name: str) -> ExtractedField:
        """Create the row of a field the document does not have yet.

        Documents processed before a field existed have no row for it.

        Args:
            document_id: Owning document.
            name: Field name.

        Returns:
            The new, unsaved field.
        """
        field = ExtractedField(
            document_id=document_id,
            label=name,
            is_predefined=True,
            status=FieldStatus.NOT_FOUND,
            attempts=0,
        )
        self._session.add(field)
        return field
