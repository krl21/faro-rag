"""Validation of individual fields from an LLM extraction answer."""

from collections.abc import Sequence
from typing import Any

from pydantic import ValidationError

from app.ai.extraction.field_specs import FieldSpec
from app.domain.dtos import FieldDraft
from app.domain.enums import FieldStatus


def validate_field(
    spec: FieldSpec, data: dict[str, Any], attempts: int, page_count: int | None = None
) -> tuple[FieldDraft | None, str]:
    """Validate one field of the LLM answer.

    Args:
        spec: Field definition.
        data: Decoded LLM answer.
        attempts: Attempts made so far (stored with the draft).
        page_count: Pages of the document; a reported page beyond it is
            dropped (``None`` skips the check).

    Returns:
        ``(draft, "")`` when the field is valid or explicitly absent, or
        ``(None, error)`` when it is invalid. An absent value (``null`` or an
        empty list) is not an error: it is stored with ``status=not_found``,
        no value, no confidence and no error, and is not retried.
    """
    if spec.key not in data:
        return None, "missing key"
    try:
        extracted = spec.adapter.validate_python(data[spec.key])
    except ValidationError as exc:
        return None, format_errors(exc)
    if extracted.value is None or extracted.value == []:
        return (
            FieldDraft(
                name=spec.name,
                value=None,
                confidence=None,
                status=FieldStatus.NOT_FOUND,
                error=None,
                attempts=attempts,
            ),
            "",
        )
    return (
        FieldDraft(
            name=spec.name,
            value=spec.adapter.dump_python(extracted, mode="json")["value"],
            confidence=extracted.confidence.value,
            status=FieldStatus.OK,
            error=None,
            attempts=attempts,
            page=_valid_page(extracted.page, page_count),
        ),
        "",
    )


def _valid_page(page: int | None, page_count: int | None) -> int | None:
    """Keep a reported page only if the document has it.

    Args:
        page: Page reported by the LLM.
        page_count: Pages of the document, or ``None`` if unknown.

    Returns:
        The page, or ``None`` when it is missing or out of range.
    """
    if page is None or (page_count is not None and page > page_count):
        return None
    return page


def spanish_key(specs: Sequence[FieldSpec], name: str) -> str:
    """Return the Spanish key of a field, as the LLM knows it.

    Args:
        specs: Field definitions.
        name: English field name.

    Returns:
        The Spanish key, or ``name`` if it is not found.
    """
    return next((s.key for s in specs if s.name == name), name)


def format_errors(exc: ValidationError) -> str:
    """Summarize a Pydantic validation error in one line.

    Args:
        exc: Validation error.

    Returns:
        ``location: message`` pairs separated by commas.
    """
    return ", ".join(
        f"{'.'.join(str(p) for p in err['loc']) or 'root'}: {err['msg']}" for err in exc.errors()
    )
