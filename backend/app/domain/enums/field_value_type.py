"""Shape of an extracted value, so the UI can pick the right editor."""

from enum import StrEnum


class FieldValueType(StrEnum):
    """Shape of an extracted value, so the UI can pick the right editor.

    Values as returned by the API: ``text`` and ``long_text`` are strings,
    ``date`` an ISO date, ``period`` ``{start, end}``, ``money``
    ``{amount, currency}`` and ``text_list`` a list of strings.
    """

    TEXT = "text"
    LONG_TEXT = "long_text"
    DATE = "date"
    PERIOD = "period"
    MONEY = "money"
    TEXT_LIST = "text_list"
