"""A structured field extracted from a document."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class ExtractedFieldOut(BaseModel):
    """A structured field extracted from a document.

    Attributes:
        name: Field name (for example ``policy_number``).
        value: Extracted value, ``None`` when it failed.
        confidence: ``low``, ``medium`` or ``high`` (shown to the user for validation).
        status: ``ok``, ``not_found`` (absent from the document) or ``failed``.
        error: Explicit error when ``status`` is ``failed``.
        attempts: LLM calls made to obtain the value.
    """

    model_config = ConfigDict(from_attributes=True)

    name: str
    value: Any | None
    confidence: str | None
    status: str
    error: str | None
    attempts: int
