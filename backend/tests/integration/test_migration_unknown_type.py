"""Migration 0005 renames the stored document type ``other`` to ``unknown``."""

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.db.session import engine
from tests.conftest import BACKEND_DIR

pytestmark = pytest.mark.integration


def _alembic(revision: str, upgrade: bool) -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    (command.upgrade if upgrade else command.downgrade)(config, revision)


def test_other_is_renamed_to_unknown_and_back(clean_database):
    _alembic("0004", upgrade=False)
    try:
        with engine.begin() as connection:
            doc_id = connection.execute(
                text(
                    "INSERT INTO documents (id, filename, content_hash, size_bytes, storage_path, "
                    "status, document_type, created_at, updated_at) VALUES (gen_random_uuid(), "
                    "'a.pdf', 'h1', 1, 'p', 'done', 'other', now(), now()) RETURNING id"
                )
            ).scalar_one()
            connection.execute(
                text(
                    "INSERT INTO extracted_fields (document_id, name, value, status, attempts) "
                    "VALUES (:id, 'document_type', '\"other\"'::jsonb, 'ok', 1)"
                ),
                {"id": doc_id},
            )
        _alembic("0005", upgrade=True)
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT document_type FROM documents WHERE id = :id"), {"id": doc_id}
                ).scalar_one()
                == "unknown"
            )
            assert (
                connection.execute(
                    text("SELECT value FROM extracted_fields WHERE document_id = :id"),
                    {"id": doc_id},
                ).scalar_one()
                == "unknown"
            )
        _alembic("0004", upgrade=False)
        with engine.connect() as connection:
            assert (
                connection.execute(
                    text("SELECT document_type FROM documents WHERE id = :id"), {"id": doc_id}
                ).scalar_one()
                == "other"
            )
    finally:
        _alembic("head", upgrade=True)
