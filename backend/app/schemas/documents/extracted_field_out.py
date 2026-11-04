"""A structured field extracted from a document."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.domain.enums import FieldValueType


class ExtractedFieldOut(BaseModel):
    """A structured field extracted from a document.

    Attributes:
        name: Field name (for example ``policy_number``).
        value: Current value (the user's one when ``edited``); ``None`` when
            not found or failed.
        confidence: ``low``, ``medium`` or ``high`` as reported by the LLM;
            ``None`` when not found, failed or edited.
        status: ``ok``, ``not_found`` (absent from the document), ``failed``
            or ``edited`` (set by the user).
        error: Explicit error when ``status`` is ``failed``.
        attempts: LLM calls made to obtain the value.
        page: 1-based page where the LLM found the value, when known.
        value_type: Shape of ``value`` (``text``, ``long_text``, ``date``,
            ``period``, ``money`` or ``text_list``), to pick the editor.
        editable: Whether ``PATCH /documents/{id}/fields/{name}`` accepts it
            (``document_type`` is not editable).
        original_value: Value extracted by the LLM before the first edit.
        edited_at: When the user last edited it.
    """

    name: str
    value: Any | None
    confidence: str | None
    status: str
    error: str | None
    attempts: int
    page: int | None = None
    value_type: FieldValueType = FieldValueType.TEXT
    editable: bool = False
    original_value: Any | None = None
    edited_at: datetime | None = None
