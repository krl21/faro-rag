"""Shared pytest fixtures.

Unit tests need nothing external. Integration tests (``tests/integration``)
use the PostgreSQL and Redis services from docker compose, a separate
``faro_test`` database and the fake LLM and embedding providers.
"""

import os
from collections.abc import Iterator
from pathlib import Path

# Safe defaults before the app reads its settings: never call real providers.
os.environ.setdefault("LLM_PROVIDER", "fake")
os.environ.setdefault("EMBEDDING_PROVIDER", "fake")
os.environ.setdefault("OTEL_ENABLED", "false")
os.environ.setdefault("STORAGE_DIR", "/tmp/faro-test-uploads")
os.environ.setdefault("EXTRACTION_RETRY_DELAYS", "[0,0]")

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def text_layer_extractor() -> Iterator[None]:
    """Make the worker read PDFs without Docling (not installed in the test image)."""
    from app.worker import tasks
    from tests.fixtures.text_layer_extractor import TextLayerExtractor

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(tasks, "DoclingExtractor", TextLayerExtractor)
        tasks.get_processor.cache_clear()
        yield
    tasks.get_processor.cache_clear()


@pytest.fixture(scope="session")
def migrated_database() -> None:
    """Apply the Alembic migrations to the test database once per session."""
    from alembic import command
    from alembic.config import Config

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(config, "head")


@pytest.fixture
def clean_database(migrated_database: None) -> Iterator[None]:
    """Empty every table and the rate-limit counters before a test."""
    import redis
    from sqlalchemy import text

    from app.config import get_settings
    from app.db.session import engine

    with engine.begin() as connection:
        connection.execute(text("TRUNCATE documents, conversations RESTART IDENTITY CASCADE"))
    redis.Redis.from_url(get_settings().redis_url).flushdb()
    yield


@pytest.fixture
def eager_celery() -> Iterator[None]:
    """Run Celery tasks synchronously in the calling process."""
    from app.worker.celery_app import celery_app

    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    yield
    celery_app.conf.task_always_eager = False


@pytest.fixture
def client(clean_database: None, eager_celery: None):
    """HTTP client for the API, with eager Celery and a clean database.

    Yields:
        A ``TestClient`` with the app lifespan running.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def settings(monkeypatch):
    """Process settings, with ``monkeypatch.setattr`` undone after the test.

    Yields:
        The cached ``Settings`` instance used by the whole app.
    """
    from app.config import get_settings

    yield get_settings()
