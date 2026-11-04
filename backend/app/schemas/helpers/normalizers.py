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
