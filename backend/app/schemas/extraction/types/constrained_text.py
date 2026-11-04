"""Constrained string types for extracted values."""

from typing import Annotated

from pydantic import StringConstraints

PolicyNumber = Annotated[str, StringConstraints(min_length=1, max_length=64)]
"""A policy number such as ``FS-2024-001``."""

ShortText = Annotated[str, StringConstraints(min_length=1, max_length=500)]
"""A short non-empty text (title, issuer, coverage name...)."""

LongText = Annotated[str, StringConstraints(min_length=1, max_length=2000)]
"""A longer non-empty text (summary)."""

Identifier = Annotated[str, StringConstraints(min_length=1, max_length=32)]
"""A short code such as a tax id (``B12345678``) or a license plate (``1234-ABC``)."""
