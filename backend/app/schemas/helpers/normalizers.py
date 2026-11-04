"""Small value normalizers shared by several schemas."""

from typing import Any


def upper_currency(value: Any) -> Any:
    """Normalize a currency code to upper case (``eur`` -> ``EUR``).

    Args:
        value: Raw currency.

    Returns:
        The stripped, upper-cased code, or ``value`` if it is not a string.
    """
    return value.strip().upper() if isinstance(value, str) else value


def none_to_empty(value: Any) -> Any:
    """Accept ``null`` as an empty string.

    Args:
        value: Raw value.

    Returns:
        ``""`` for ``None``, else ``value``.
    """
    return "" if value is None else value


def page_or_none(value: Any) -> int | None:
    """Accept a 1-based page number, turning anything else into ``None``.

    The page is a hint for the user, so an unusable value (``0``, ``"última"``,
    ``-3``) is dropped instead of rejecting the whole LLM answer.

    Args:
        value: Raw page number.

    Returns:
        The page as a positive integer, or ``None``.
    """
    if isinstance(value, bool):
        return None
    try:
        page = int(value)
    except (TypeError, ValueError):
        return None
    return page if page >= 1 else None
