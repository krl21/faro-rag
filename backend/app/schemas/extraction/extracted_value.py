"""A value extracted by the LLM with its confidence."""

from typing import Annotated, Generic, TypeVar

from pydantic import BeforeValidator, Field

from app.domain.enums import Confidence
from app.schemas.extraction.spanish_input import SpanishInput
from app.schemas.helpers import confidence_from_spanish

T = TypeVar("T")


class ExtractedValue(SpanishInput, Generic[T]):  # noqa: UP046 - Pydantic generic model
    """A value extracted by the LLM with its confidence.

    Attributes:
        value: Extracted value, or ``None`` when the document does not contain it.
        confidence: Confidence the LLM reports (``baja``/``media``/``alta`` on input).
    """

    value: T | None = Field(default=None, alias="valor")
    confidence: Annotated[Confidence, BeforeValidator(confidence_from_spanish)] = Field(
        alias="confianza"
    )
