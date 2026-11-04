"""Migration 0006 moves the filter index from field_values into extracted_fields."""

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.db.session import engine
from tests.conftest import BACKEND_DIR

pytestmark = pytest.mark.integration


def _alembic(revision: str, upgrade: bool) -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    (command.upgrade if upgrade else command.downgrade)(config, revision)


def test_values_are_copied_and_the_table_dropped(clean_database):
    _alembic("0005", upgrade=False)
    try:
        with engine.begin() as connection:
            doc_id = connection.execute(
                text(
                    "INSERT INTO documents (id, filename, content_hash, size_bytes, storage_path, "
                    "status, document_type, created_at, updated_at) VALUES (gen_random_uuid(), "
                    "'f.pdf', 'h6', 1, 'p', 'done', 'invoice', now(), now()) RETURNING id"
                )
            ).scalar_one()
            for name, value in (
                ("invoice_amount", '{"amount": "10.00", "currency": "EUR"}'),
                ("policy_number", '"FS-1"'),
            ):
                connection.execute(
                    text(
                        "INSERT INTO extracted_fields (document_id, name, value, status, attempts) "
                        "VALUES (:id, :name, CAST(:value AS jsonb), 'ok', 1)"
                    ),
                    {"id": doc_id, "name": name, "value": value},
                )
            connection.execute(
                text(
                    "INSERT INTO field_values (document_id, field_name, number_value, currency) "
                    "VALUES (:id, 'invoice_amount', 10.00, 'EUR'), "
                    "(:id, 'policy_number', NULL, NULL)"
                ),
                {"id": doc_id},
            )
            connection.execute(
                text(
                    "UPDATE field_values SET text_value = 'FS1' "
                    "WHERE document_id = :id AND field_name = 'policy_number'"
                ),
                {"id": doc_id},
            )
        _alembic("0006", upgrade=True)
        assert "field_values" not in inspect(engine).get_table_names()
        with engine.connect() as connection:
            rows = dict(
                connection.execute(
                    text(
                        "SELECT name, COALESCE(text_value, number_value::text || ' ' || currency) "
                        "FROM extracted_fields WHERE document_id = :id"
                    ),
                    {"id": doc_id},
                ).all()
            )
        assert rows == {"invoice_amount": "10.00 EUR", "policy_number": "FS1"}

        _alembic("0005", upgrade=False)
        with engine.connect() as connection:
            restored = connection.execute(
                text("SELECT count(*) FROM field_values WHERE document_id = :id"), {"id": doc_id}
            ).scalar_one()
        assert restored == 2
    finally:
        _alembic("head", upgrade=True)
