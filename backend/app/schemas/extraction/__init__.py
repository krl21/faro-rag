"""Pydantic models that validate the LLM extraction output.

The prompts are in Spanish, so the LLM answers with Spanish keys and values
(``numero_poliza``, ``confianza: "alta"``...). These models accept that input
through aliases and expose English names and values to the rest of the code.

One module per class; this package re-exports the public names.
"""

from app.schemas.extraction.classification import Classification
from app.schemas.extraction.extracted_value import ExtractedValue
from app.schemas.extraction.money import Money
from app.schemas.extraction.types import Identifier, LongText, PolicyNumber, ShortText
from app.schemas.extraction.validity import Validity

__all__ = [
    "Classification",
    "ExtractedValue",
    "Identifier",
    "LongText",
    "Money",
    "PolicyNumber",
    "ShortText",
    "Validity",
]
