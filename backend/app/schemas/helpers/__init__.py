"""Common functions of the schemas (not models): translation, aliases, normalizers."""

from app.schemas.helpers.aliases import spanish_alias
from app.schemas.helpers.normalizers import none_to_empty, upper_currency
from app.schemas.helpers.translation import (
    CONFIDENCE_ES,
    DOCUMENT_TYPE_ES,
    FIELD_ES,
    confidence_from_spanish,
    document_type_from_spanish,
    filter_field_from_spanish,
    translate,
)

__all__ = [
    "CONFIDENCE_ES",
    "DOCUMENT_TYPE_ES",
    "FIELD_ES",
    "confidence_from_spanish",
    "document_type_from_spanish",
    "filter_field_from_spanish",
    "none_to_empty",
    "spanish_alias",
    "translate",
    "upper_currency",
]
