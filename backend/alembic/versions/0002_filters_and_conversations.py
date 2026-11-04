"""Chat filters and conversations: field_values index, document indexes, conversations.

``field_values`` is filled when a document is processed. Documents processed
before this migration have no rows there, so chat filters ignore them until
they are processed again (in development: ``make clean`` and upload again).

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the trigram extension, the new tables and the indexes."""
    # Standard PostgreSQL contrib extension: makes LIKE '%...%' indexable.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_index("ix_documents_document_type", "documents", ["document_type"])
    op.create_index("ix_documents_created_at", "documents", ["created_at"])

    op.create_table(
        "field_values",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_name", sa.String(64), nullable=False),
        sa.Column("text_value", sa.String(255)),
        sa.Column("number_value", sa.Numeric(14, 2)),
        sa.Column("currency", sa.String(3)),
        sa.Column("date_from", sa.Date()),
        sa.Column("date_to", sa.Date()),
    )
    op.create_index("ix_field_values_document_id", "field_values", ["document_id"])
    op.create_index("ix_field_values_text", "field_values", ["field_name", "text_value"])
    op.create_index(
        "ix_field_values_text_trgm",
        "field_values",
        ["text_value"],
        postgresql_using="gin",
        postgresql_ops={"text_value": "gin_trgm_ops"},
    )
    op.create_index("ix_field_values_number", "field_values", ["field_name", "number_value"])
    op.create_index("ix_field_values_dates", "field_values", ["field_name", "date_from", "date_to"])

    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "messages",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    """Drop the new tables and indexes (the extension is left in place)."""
    op.drop_table("conversations")
    op.drop_table("field_values")
    op.drop_index("ix_documents_created_at", table_name="documents")
    op.drop_index("ix_documents_document_type", table_name="documents")
