"""Stored form of the value of a free datum (text, or the columns of a table row).

A JSONB object does not keep the order of its keys (PostgreSQL sorts them),
so a table row is stored as a list of ``{"column", "value"}`` and turned back
into an ordered ``dict`` when read. Text values are stored as they are.
"""

from typing import Any


def to_stored(value: str | dict[str, str]) -> str | list[dict[str, str]]:
    """Turn a value into its stored JSON form.

    Args:
        value: Text, or the columns of a table row in their order.

    Returns:
        The text, or a list of ``{"column": ..., "value": ...}``.
    """
    if isinstance(value, dict):
        return [{"column": column, "value": cell} for column, cell in value.items()]
    return value


def from_stored(value: Any) -> str | dict[str, str]:
    """Turn a stored value back into text or an ordered ``dict`` of columns.

    Args:
        value: Value read from ``extracted_fields.value``.

    Returns:
        The text, or the columns of the row in their original order.
    """
    if isinstance(value, list):
        return {str(cell["column"]): str(cell["value"]) for cell in value if isinstance(cell, dict)}
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items()}
    return "" if value is None else str(value)
