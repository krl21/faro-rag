"""A value extracted by the LLM with its confidence."""

from typing import Annotated, Generic, TypeVar

from pydantic import BeforeValidator, Field

from app.domain.enums import Confidence
from app.schemas.extraction.spanish_input import SpanishInput
from app.schemas.helpers import confidence_from_spanish, page_or_none

T = TypeVar("T")


class ExtractedValue(SpanishInput, Generic[T]):  # noqa: UP046 - Pydantic generic model
    """A value extracted by the LLM with its confidence.

    Attributes:
        value: Extracted value, or ``None`` when the document does not contain it.
        confidence: Confidence the LLM reports (``baja``/``media``/``alta`` on input).
        page: 1-based page where the value appears (``pagina`` on input);
            ``None`` when unknown or unusable.
    """

    value: T | None = Field(default=None, alias="valor")
    confidence: Annotated[Confidence, BeforeValidator(confidence_from_spanish)] = Field(
        alias="confianza"
    )
    page: Annotated[int | None, BeforeValidator(page_or_none)] = Field(default=None, alias="pagina")
