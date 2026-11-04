"""ORM model for the ``extracted_fields`` table."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base

if TYPE_CHECKING:
    from app.db.models.document import Document


class ExtractedField(Base):
    """A structured value extracted from a document, one row per field.

    ``value`` keeps the value as shown and edited (JSON). The typed columns
    (``text_value``, ``number_value`` + ``currency``, ``date_from`` /
    ``date_to``) hold a normalized copy used by the chat filters, with
    indexes; only the column that fits the field is set, and none for fields
    that are not filterable or have no value.

    When the user edits a field, ``status`` becomes ``edited``, ``value`` holds
    the user's value and ``original_value`` keeps the value extracted by the
    LLM (only the first time, so later edits never lose it).
    """

    __tablename__ = "extracted_fields"
    __table_args__ = (
        UniqueConstraint("document_id", "name", name="uq_field_per_document"),
        Index("ix_extracted_fields_text", "name", "text_value"),
        Index(
            "ix_extracted_fields_text_trgm",
            "text_value",
            postgresql_using="gin",
            postgresql_ops={"text_value": "gin_trgm_ops"},
        ),
        Index("ix_extracted_fields_number", "name", "number_value"),
        Index("ix_extracted_fields_dates", "name", "date_from", "date_to"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(64))
    value: Mapped[Any | None] = mapped_column(JSONB)
    confidence: Mapped[str | None] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(10))
    error: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    page: Mapped[int | None] = mapped_column(Integer)
    original_value: Mapped[Any | None] = mapped_column(JSONB)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Filter columns: normalized copy of ``value`` for the chat filters.
    text_value: Mapped[str | None] = mapped_column(String(255))
    number_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    date_from: Mapped[date | None] = mapped_column(Date)
    date_to: Mapped[date | None] = mapped_column(Date)

    document: Mapped["Document"] = relationship(back_populates="fields")

    def set_filter_columns(
        self,
        *,
        text_value: str | None = None,
        number_value: Decimal | None = None,
        currency: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> None:
        """Replace every filter column (unset ones become ``None``).

        Args:
            text_value: Normalized identifier or name.
            number_value: Amount.
            currency: ISO 4217 code of the amount.
            date_from: First day of the date or period.
            date_to: Last day of the date or period.
        """
        self.text_value = text_value
        self.number_value = number_value
        self.currency = currency
        self.date_from = date_from
        self.date_to = date_to
