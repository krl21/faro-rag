"""Declarative base shared by every ORM model."""

from datetime import UTC, datetime

from sqlalchemy.orm import DeclarativeBase


def utcnow() -> datetime:
    """Return the current UTC time.

    Returns:
        A timezone-aware ``datetime``.
    """
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Declarative base for every model."""
