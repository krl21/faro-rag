"""An extracted field ready to be stored."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FieldDraft:
    """An extracted field ready to be stored.

    Attributes:
        name: Field name in English (for example ``policy_number``).
        value: JSON-serializable value, or ``None`` when extraction failed.
        confidence: ``low``, ``medium`` or ``high``; ``None`` when it failed.
        status: ``ok``, ``not_found``, ``failed`` or ``edited``.
        error: Explicit error when ``status`` is ``failed``.
        attempts: Number of LLM calls made for this field.
        page: 1-based page where the value was found, when the LLM reports it.
    """

    name: str
    value: Any | None
    confidence: str | None
    status: str
    error: str | None
    attempts: int
    page: int | None = None
