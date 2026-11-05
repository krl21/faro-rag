"""Free label-value data in ``extracted_fields``.

Besides the known fields, every label-value datum found in the tables and
"campo: valor" lines of a document is stored in the same table, with an empty
``name``, its ``label`` as written, its position in the table and an embedding
used by the chat to pick the data relevant to a question.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

from app.config import get_settings

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the columns of the free data and allow rows without ``name``."""
    op.alter_column("extracted_fields", "name", existing_type=sa.String(64), nullable=True)
    op.add_column("extracted_fields", sa.Column("label", sa.String(255)))
    op.add_column("extracted_fields", sa.Column("table_index", sa.Integer()))
    op.add_column("extracted_fields", sa.Column("row_index", sa.Integer()))
    op.add_column("extracted_fields", sa.Column("embedding", Vector(get_settings().embedding_dim)))


def downgrade() -> None:
    """Delete the free data and drop their columns."""
    op.execute("DELETE FROM extracted_fields WHERE name IS NULL")
    for column in ("embedding", "row_index", "table_index", "label"):
        op.drop_column("extracted_fields", column)
    op.alter_column("extracted_fields", "name", existing_type=sa.String(64), nullable=False)
