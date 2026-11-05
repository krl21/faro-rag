"""One key column for every datum: ``label``, plus ``is_predefined``.

Fixed fields kept their key in ``name`` and free data in ``label``. Both are
``(label, value)`` pairs, so ``name`` is merged into ``label`` and the boolean
``is_predefined`` tells them apart. The uniqueness per document applies only to the
fixed fields (free labels repeat). Table rows are stored as a list of
``{"column", "value"}`` so the order of their columns is kept (a JSONB object
does not keep the order of its keys).

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_KEY_INDEXES = {
    "ix_extracted_fields_text": ["text_value"],
    "ix_extracted_fields_number": ["number_value"],
    "ix_extracted_fields_dates": ["date_from", "date_to"],
}


def upgrade() -> None:
    """Merge ``name`` into ``label`` and add ``is_predefined``."""
    op.add_column(
        "extracted_fields",
        sa.Column("is_predefined", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(
        "UPDATE extracted_fields SET is_predefined = true, label = name WHERE name IS NOT NULL"
    )
    # Table rows: object -> ordered list (the current order is the one JSONB kept).
    op.execute(
        """
        UPDATE extracted_fields
        SET value = (
            SELECT jsonb_agg(jsonb_build_object('column', key, 'value', val))
            FROM jsonb_each_text(value) AS cells(key, val)
        )
        WHERE NOT is_predefined AND jsonb_typeof(value) = 'object'
        """
    )
    op.execute("UPDATE extracted_fields SET label = '' WHERE label IS NULL")
    op.alter_column("extracted_fields", "label", existing_type=sa.String(255), nullable=False)

    op.drop_constraint("uq_field_per_document", "extracted_fields", type_="unique")
    for index, columns in _KEY_INDEXES.items():
        op.drop_index(index, table_name="extracted_fields")
        op.create_index(index, "extracted_fields", ["label", *columns])
    op.drop_column("extracted_fields", "name")
    op.create_index(
        "uq_predefined_field_per_document",
        "extracted_fields",
        ["document_id", "label"],
        unique=True,
        postgresql_where=sa.text("is_predefined"),
    )


def downgrade() -> None:
    """Split ``label`` back into ``name`` (fixed fields) and ``label`` (free data)."""
    op.add_column("extracted_fields", sa.Column("name", sa.String(64)))
    op.alter_column("extracted_fields", "label", existing_type=sa.String(255), nullable=True)
    op.execute("UPDATE extracted_fields SET name = label, label = NULL WHERE is_predefined")
    op.execute(
        """
        UPDATE extracted_fields
        SET value = (
            SELECT jsonb_object_agg(cell->>'column', cell->>'value')
            FROM jsonb_array_elements(value) AS cell
        )
        WHERE NOT is_predefined AND jsonb_typeof(value) = 'array'
        """
    )
    op.drop_index("uq_predefined_field_per_document", table_name="extracted_fields")
    for index, columns in _KEY_INDEXES.items():
        op.drop_index(index, table_name="extracted_fields")
        op.create_index(index, "extracted_fields", ["name", *columns])
    op.create_unique_constraint(
        "uq_field_per_document", "extracted_fields", ["document_id", "name"]
    )
    op.drop_column("extracted_fields", "is_predefined")
