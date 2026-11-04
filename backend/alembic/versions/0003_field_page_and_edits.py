"""Extracted fields: source page and user edits (original value and edit time).

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the page, original value and edit time columns."""
    op.add_column("extracted_fields", sa.Column("page", sa.Integer()))
    op.add_column("extracted_fields", sa.Column("original_value", postgresql.JSONB()))
    op.add_column("extracted_fields", sa.Column("edited_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    """Drop the columns."""
    op.drop_column("extracted_fields", "edited_at")
    op.drop_column("extracted_fields", "original_value")
    op.drop_column("extracted_fields", "page")
