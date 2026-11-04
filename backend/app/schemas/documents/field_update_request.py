"""Body of ``PATCH /documents/{id}/fields/{name}``."""

from typing import Any

from pydantic import BaseModel


class FieldUpdateRequest(BaseModel):
    """New value of a field, typed by the user.

    Attributes:
        value: Same shape as ``ExtractedFieldOut.value`` for the field's
            ``value_type``: a string, an ISO date (``"2025-03-15"``),
            ``{"start": ..., "end": ...}``, ``{"amount": ..., "currency": ...}``
            or a list of strings.
    """

    value: Any
