"""Rename the document type ``other`` to ``unknown`` in the stored data.

Updates ``documents.document_type`` and the ``document_type`` extracted field.
Filters stored in conversation history keep the old value: they are only
shown as history and never re-run.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-04
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Replace ``other`` with ``unknown``."""
    _rename("other", "unknown")


def downgrade() -> None:
    """Restore ``other``."""
    _rename("unknown", "other")


def _rename(old: str, new: str) -> None:
    """Rename a document type in both places it is stored.

    Args:
        old: Current value.
        new: New value.
    """
    op.execute(f"UPDATE documents SET document_type = '{new}' WHERE document_type = '{old}'")  # noqa: S608
    op.execute(
        f"UPDATE extracted_fields SET value = '\"{new}\"'::jsonb "  # noqa: S608
        f"WHERE name = 'document_type' AND value = '\"{old}\"'::jsonb"
    )
