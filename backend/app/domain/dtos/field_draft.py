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
        status: ``ok`` or ``failed``.
        error: Explicit error when ``status`` is ``failed``.
        attempts: Number of LLM calls made for this field.
    """

    name: str
    value: Any | None
    confidence: str | None
    status: str
    error: str | None
    attempts: int
