"""Outcome of extracting one field."""

from enum import StrEnum


class FieldStatus(StrEnum):
    """Outcome of extracting one field."""

    OK = "ok"
    NOT_FOUND = "not_found"  # The document does not contain the value: not an error.
    FAILED = "failed"
