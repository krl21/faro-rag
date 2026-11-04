"""Edition of extracted fields by the user."""

import uuid

from fastapi import APIRouter

from app.api.deps import FieldEditServiceDep
from app.api.mappers import to_field_out
from app.schemas.documents import ExtractedFieldOut, FieldUpdateRequest

router = APIRouter(prefix="/documents", tags=["documents"])


@router.patch(
    "/{document_id}/fields/{field_name}",
    response_model=ExtractedFieldOut,
    responses={
        404: {"description": "document_not_found or field_not_found"},
        409: {"description": "document_not_ready: the document is not processed"},
        422: {"description": "invalid_field_value: the value has the wrong shape"},
    },
)
def update_field(
    document_id: uuid.UUID,
    field_name: str,
    body: FieldUpdateRequest,
    service: FieldEditServiceDep,
) -> ExtractedFieldOut:
    """Set or correct the value of a field (status becomes ``edited``).

    The value is validated with the same type as the LLM output; the LLM value
    is kept in ``original_value`` and the chat filters use the new value.

    Args:
        document_id: Document identifier.
        field_name: Field name, for example ``policy_number``.
        body: New value.
        service: Field edit service.

    Returns:
        The updated field.
    """
    field, document_type = service.edit(document_id, field_name, body.value)
    return to_field_out(field, document_type)
