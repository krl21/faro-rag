"""Translate chat filters into SQL over ``documents`` and ``extracted_fields``.

Every condition uses an indexed column: ``documents.document_type`` and
``created_at``, and the filter columns of ``extracted_fields`` by ``(name, text_value)``, trigram
on ``text_value``, ``(field_name, number_value)`` and ``(field_name,
date_from, date_to)``. Values are always bound parameters, never SQL text.
"""

import uuid
from collections.abc import Sequence
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import ColumnElement, Select, and_, exists, false, not_, or_, select
from sqlalchemy.orm import Session

from app.core.text_normalization import normalize_identifier, normalize_name
from app.db.models import Document, ExtractedField
from app.domain.enums import DocumentStatus, DocumentType, FilterField
from app.domain.indexed_fields import AMOUNT_FIELD, DOCUMENT_DATE_FIELDS, is_identifier
from app.schemas.filters import AmountRange, DateRange, FieldValues, QueryFilters


def _escape_like(value: str) -> str:
    r"""Escape the ``LIKE`` wildcards of a value.

    Args:
        value: Normalized value.

    Returns:
        The value with ``%``, ``_`` and ``\\`` escaped.
    """
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _local_bounds(range_: DateRange, tz: ZoneInfo) -> tuple[datetime | None, datetime | None]:
    """Convert a local date range into ``[start, end)`` instants.

    Args:
        range_: Inclusive local dates.
        tz: Time zone the dates are expressed in.

    Returns:
        Start of the first day and start of the day after the last one.
    """
    start = datetime.combine(range_.start, time.min, tz) if range_.start else None
    end = datetime.combine(range_.end + timedelta(days=1), time.min, tz) if range_.end else None
    return start, end


class DocumentFilterRepository:
    """Find the processed documents that match a set of filters."""

    def __init__(self, session: Session, tz: ZoneInfo) -> None:
        """Create the repository.

        Args:
            session: Active SQLAlchemy session.
            tz: Time zone used for the upload date filter.
        """
        self._session = session
        self._tz = tz

    def matching_ids(self, filters: QueryFilters) -> list[uuid.UUID]:
        """Return the ids of the ``done`` documents that match every filter.

        Args:
            filters: Filters of the question.

        Returns:
            Matching document ids (possibly empty).
        """
        stmt = self._build(select(Document.id), filters)
        return list(self._session.scalars(stmt))

    def matching_documents(self, filters: QueryFilters, limit: int) -> list[Document]:
        """Return the matching documents, newest first.

        Args:
            filters: Filters of the question.
            limit: Maximum documents returned.

        Returns:
            The documents.
        """
        stmt = self._build(select(Document), filters)
        stmt = stmt.order_by(Document.created_at.desc()).limit(limit)
        return list(self._session.scalars(stmt))

    def _build(self, stmt: Select, filters: QueryFilters) -> Select:
        """Add the filter conditions to a query on ``documents``.

        Args:
            stmt: Base query.
            filters: Filters of the question.

        Returns:
            The filtered query.
        """
        conditions: list[ColumnElement[bool]] = [
            Document.status == DocumentStatus.DONE,
            # The chat only works with policies and invoices.
            Document.document_type.is_distinct_from(DocumentType.UNKNOWN.value),
        ]
        if filters.document_type:
            conditions.append(Document.document_type == filters.document_type.value)
        if filters.uploaded:
            start, end = _local_bounds(filters.uploaded, self._tz)
            if start:
                conditions.append(Document.created_at >= start)
            if end:
                conditions.append(Document.created_at < end)
        if filters.document_date:
            conditions.append(self._document_date(filters.document_date))
        if filters.amount:
            conditions.append(self._amount(filters.amount))
        conditions.extend(self._group(group) for group in filters.include)
        conditions.extend(not_(self._group(group)) for group in filters.exclude)
        return stmt.where(and_(*conditions))

    @staticmethod
    def _value_exists(*conditions: ColumnElement[bool]) -> ColumnElement[bool]:
        """Build ``EXISTS`` over the values of the current document.

        Args:
            *conditions: Conditions on ``extracted_fields``.

        Returns:
            The ``EXISTS`` clause.
        """
        return exists().where(ExtractedField.document_id == Document.id, *conditions)

    def _group(self, group: FieldValues) -> ColumnElement[bool]:
        """Condition for one include/exclude group: the field has any of the values.

        Args:
            group: Field and accepted values.

        Returns:
            The condition.
        """
        if group.field is FilterField.DOCUMENT_TYPE:
            return Document.document_type.in_(group.values)
        if is_identifier(group.field):
            normalized = [normalize_identifier(v) for v in group.values]
            return self._value_exists(
                ExtractedField.name == group.field.value,
                ExtractedField.text_value.in_([v for v in normalized if v]),
            )
        # A value with only punctuation normalizes to "" and would match
        # everything with LIKE '%%': such values match nothing instead.
        names = [n for n in (normalize_name(v) for v in group.values) if n]
        if not names:
            return false()
        patterns = [f"%{_escape_like(n)}%" for n in names]
        return self._value_exists(
            ExtractedField.name == group.field.value,
            or_(*(ExtractedField.text_value.like(p, escape="\\") for p in patterns)),
        )

    def _document_date(self, range_: DateRange) -> ColumnElement[bool]:
        """Condition: a document date (or validity period) overlaps the range.

        Args:
            range_: Inclusive dates.

        Returns:
            The condition.
        """
        conditions: list[ColumnElement[bool]] = [
            ExtractedField.name.in_(sorted(DOCUMENT_DATE_FIELDS))
        ]
        if range_.end:
            conditions.append(ExtractedField.date_from <= range_.end)
        if range_.start:
            conditions.append(ExtractedField.date_to >= range_.start)
        return self._value_exists(*conditions)

    def _amount(self, range_: AmountRange) -> ColumnElement[bool]:
        """Condition: the invoice amount is inside the range.

        Args:
            range_: Amount bounds and optional currency.

        Returns:
            The condition.
        """
        conditions: list[ColumnElement[bool]] = [ExtractedField.name == AMOUNT_FIELD]
        if range_.min is not None:
            conditions.append(ExtractedField.number_value >= range_.min)
        if range_.max is not None:
            conditions.append(ExtractedField.number_value <= range_.max)
        if range_.currency:
            conditions.append(ExtractedField.currency == range_.currency)
        return self._value_exists(*conditions)


def restrict_ids(
    matching: Sequence[uuid.UUID] | None, document_id: uuid.UUID | None
) -> list[uuid.UUID] | None:
    """Combine the filter result with an explicit document restriction.

    Args:
        matching: Ids matching the filters, or ``None`` when there are no filters.
        document_id: Document the client restricted the question to.

    Returns:
        The ids to search in, or ``None`` to search every document.
    """
    if document_id is None:
        return None if matching is None else list(matching)
    if matching is None:
        return [document_id]
    return [document_id] if document_id in matching else []
