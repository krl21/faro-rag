"""ORM model for the ``extracted_fields`` table."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    false,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import get_settings
from app.db.models.base import Base

if TYPE_CHECKING:
    from app.db.models.document import Document


class ExtractedField(Base):
    """A label-value datum of a document: a fixed field or a free datum.

    Every row is a ``(label, value)`` pair; ``is_predefined`` tells the two kinds apart:

    - **Fixed fields** (``is_predefined``): the known list of each document type.
      ``label`` is the field key (``invoice_amount``, ``holder``...), unique
      per document; extracted by the LLM and validated by type. They feed the
      filters, the field screen and the chat.
    - **Free data** (not ``is_predefined``): every label-value datum found in the
      tables and "campo: valor" lines of the document. ``label`` is the label
      as written (``TOTAL FACTURA``) and may repeat; ``value`` is the text as
      written or, for a table row, its columns (stored as a list of
      ``{"column", "value"}`` so their order is kept, see ``fact_values``).
      They are not validated by type and have no filter columns;
      ``embedding`` lets the chat pick the ones relevant to a question.

    The user can edit and delete both kinds.

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
        # One row per fixed field and document; free labels may repeat.
        Index(
            "uq_predefined_field_per_document",
            "document_id",
            "label",
            unique=True,
            postgresql_where=text("is_predefined"),
        ),
        Index("ix_extracted_fields_text", "label", "text_value"),
        Index(
            "ix_extracted_fields_text_trgm",
            "text_value",
            postgresql_using="gin",
            postgresql_ops={"text_value": "gin_trgm_ops"},
        ),
        Index("ix_extracted_fields_number", "label", "number_value"),
        Index("ix_extracted_fields_dates", "label", "date_from", "date_to"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str] = mapped_column(String(255))
    is_predefined: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
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

    # Free data only: position in its table and embedding of ``label: value``.
    table_index: Mapped[int | None] = mapped_column(Integer)
    row_index: Mapped[int | None] = mapped_column(Integer)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(get_settings().embedding_dim))

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
