"""Definition of the extractable fields: the FieldSpec class and the per-type table."""

from app.ai.extraction.specs.field_spec import FieldSpec
from app.ai.extraction.specs.field_specs import COMMON_FIELD_SPECS, FIELD_SPECS, find_spec

__all__ = [
    "COMMON_FIELD_SPECS",
    "FIELD_SPECS",
    "FieldSpec",
    "find_spec",
]
