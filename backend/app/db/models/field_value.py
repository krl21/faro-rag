"""ORM model for the ``field_values`` table (the filter index)."""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Date, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class FieldValue(Base):
    """One indexed value of an extracted field, used to filter documents in SQL.

    ``extracted_fields`` keeps each field as JSON for display. This table
    flattens the filterable ones into typed, indexed columns: one row per
    atomic value (a list yields several rows). Only the column that applies to
    the field is filled:

    - ``text_value``: normalized identifier (exact match) or name (partial
      match through a trigram index).
    - ``number_value`` + ``currency``: amounts.
    - ``date_from`` / ``date_to``: single dates (both equal) or periods.
    """

    __tablename__ = "field_values"
    __table_args__ = (
        Index("ix_field_values_text", "field_name", "text_value"),
        Index(
            "ix_field_values_text_trgm",
            "text_value",
            postgresql_using="gin",
            postgresql_ops={"text_value": "gin_trgm_ops"},
        ),
        Index("ix_field_values_number", "field_name", "number_value"),
        Index("ix_field_values_dates", "field_name", "date_from", "date_to"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    field_name: Mapped[str] = mapped_column(String(64))
    text_value: Mapped[str | None] = mapped_column(String(255))
    number_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    date_from: Mapped[date | None] = mapped_column(Date)
    date_to: Mapped[date | None] = mapped_column(Date)
