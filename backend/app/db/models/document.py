"""ORM model for the ``documents`` table."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, utcnow
from app.domain.enums import DocumentStatus

if TYPE_CHECKING:
    from app.db.models.chunk import Chunk
    from app.db.models.extracted_field import ExtractedField


class Document(Base):
    """An uploaded PDF and its processing state."""

    __tablename__ = "documents"
    __table_args__ = (
        # Chat filters: "facturas", "subidas ayer".
        Index("ix_documents_document_type", "document_type"),
        Index("ix_documents_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String(255))
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    storage_path: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(20), default=DocumentStatus.PENDING, index=True)
    document_type: Mapped[str | None] = mapped_column(String(20))
    page_count: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True
    )
    # Fixed fields only (``is_predefined``); the free data are read with ``facts``.
    fields: Mapped[list["ExtractedField"]] = relationship(
        back_populates="document",
        primaryjoin="and_(Document.id == ExtractedField.document_id, "
        "ExtractedField.is_predefined.is_(True))",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ExtractedField.label",
    )
    facts: Mapped[list["ExtractedField"]] = relationship(
        primaryjoin="and_(Document.id == ExtractedField.document_id, "
        "ExtractedField.is_predefined.is_(False))",
        viewonly=True,
        order_by="(ExtractedField.page, ExtractedField.table_index, "
        "ExtractedField.row_index, ExtractedField.id)",
    )
