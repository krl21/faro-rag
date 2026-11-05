"""Merge ``field_values`` into ``extracted_fields`` (one row per field).

Every filterable field now holds a single value, so the typed filter columns
can live in the same row as the field: no second table to keep in sync. The
data is copied from ``field_values`` and that table is dropped.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = ("text_value", "number_value", "currency", "date_from", "date_to")


def upgrade() -> None:
    """Add the filter columns, copy the values and drop ``field_values``."""
    op.add_column("extracted_fields", sa.Column("text_value", sa.String(255)))
    op.add_column("extracted_fields", sa.Column("number_value", sa.Numeric(14, 2)))
    op.add_column("extracted_fields", sa.Column("currency", sa.String(3)))
    op.add_column("extracted_fields", sa.Column("date_from", sa.Date()))
    op.add_column("extracted_fields", sa.Column("date_to", sa.Date()))

    # One value per filterable field, so each field_values row maps to one field row.
    op.execute(
        """
        UPDATE extracted_fields AS f
        SET text_value = v.text_value,
            number_value = v.number_value,
            currency = v.currency,
            date_from = v.date_from,
            date_to = v.date_to
        FROM field_values AS v
        WHERE v.document_id = f.document_id AND v.field_name = f.name
        """
    )

    op.create_index("ix_extracted_fields_text", "extracted_fields", ["name", "text_value"])
    op.create_index(
        "ix_extracted_fields_text_trgm",
        "extracted_fields",
        ["text_value"],
        postgresql_using="gin",
        postgresql_ops={"text_value": "gin_trgm_ops"},
    )
    op.create_index("ix_extracted_fields_number", "extracted_fields", ["name", "number_value"])
    op.create_index(
        "ix_extracted_fields_dates", "extracted_fields", ["name", "date_from", "date_to"]
    )
    op.drop_table("field_values")


def downgrade() -> None:
    """Recreate ``field_values`` from the filter columns and drop them."""
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
    op.execute(
        """
        INSERT INTO field_values
            (document_id, field_name, text_value, number_value, currency, date_from, date_to)
        SELECT document_id, name, text_value, number_value, currency, date_from, date_to
        FROM extracted_fields
        WHERE text_value IS NOT NULL OR number_value IS NOT NULL OR date_from IS NOT NULL
        """
    )
    for index in ("text", "text_trgm", "number", "dates"):
        op.drop_index(f"ix_extracted_fields_{index}", table_name="extracted_fields")
    for column in _COLUMNS:
        op.drop_column("extracted_fields", column)
