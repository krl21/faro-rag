"""ORM model for the ``extracted_fields`` table."""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base

if TYPE_CHECKING:
    from app.db.models.document import Document


class ExtractedField(Base):
    """A structured value extracted from a document."""

    __tablename__ = "extracted_fields"
    __table_args__ = (UniqueConstraint("document_id", "name", name="uq_field_per_document"),)

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

    document: Mapped["Document"] = relationship(back_populates="fields")
