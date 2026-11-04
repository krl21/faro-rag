"""Use case: the user sets or corrects the value of an extracted field."""

import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.extraction.field_indexing import build_field_values
from app.ai.extraction.field_specs import FieldSpec, find_spec
from app.ai.extraction.field_validation import format_errors
from app.core.errors import (
    DocumentNotFoundError,
    DocumentNotReadyError,
    FieldNotFoundError,
    InvalidFieldValueError,
)
from app.core.telemetry import get_tracer
from app.db.models import ExtractedField
from app.db.repositories import DocumentRepository, FieldRepository, FieldValueRepository
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
        self._field_values = FieldValueRepository(session)
        self._clock = clock

    def edit(self, document_id: uuid.UUID, name: str, value: Any) -> tuple[ExtractedField, str]:
        """Replace the value of a field with one given by the user.

        Works for any field of the document type, including ``not_found`` and
        ``failed`` ones (the user fills in the missing value). The value is
        validated with the same Pydantic type as the LLM output. The LLM value
        is kept in ``original_value`` the first time, and the chat filter index
        of that field is rebuilt in the same transaction.

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
            self._field_values.replace_for_field(document_id, name, build_field_values([draft]))
            self._session.commit()
            self._session.refresh(field)
            logger.info(
                "field edited by the user", extra={"document_id": str(document_id), "field": name}
            )
            return field, document.document_type

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
            document_id=document_id, name=name, status=FieldStatus.NOT_FOUND, attempts=0
        )
        self._session.add(field)
        return field
