"""Structured filters extracted from a chat question.

The LLM answers with the Spanish format of the prompt (``tipo_documento``,
``fecha_subida``, ``incluir``...). These models accept both the Spanish keys
and the English names, and expose English names to the code and the API, so
the frontend can show the filters and send them back edited.

One module per class; this package re-exports the public names.
"""

from app.schemas.filters.amount_range import AmountRange
from app.schemas.filters.date_range import DateRange
from app.schemas.filters.field_values import FieldValues
from app.schemas.filters.query_filters import QueryFilters
from app.schemas.filters.types import FilterValue

__all__ = [
    "AmountRange",
    "DateRange",
    "FieldValues",
    "FilterValue",
    "QueryFilters",
]
