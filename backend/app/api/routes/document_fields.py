"""Edition of extracted fields by the user."""

import logging
import uuid

from fastapi import APIRouter, Response, status

from app.api.deps import FieldEditServiceDep
from app.api.mappers import to_field_out
from app.core.flow_logging import fields
from app.schemas.documents import ExtractedFieldOut, FieldUpdateRequest

logger = logging.getLogger(__name__)

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
    logger.debug(
        "field edit received",
        extra=fields(document_id=str(document_id), field=field_name, value=body.value),
    )
    field, document_type = service.edit(document_id, field_name, body.value)
    return to_field_out(field, document_type)


@router.delete(
    "/{document_id}/fields/{field_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"description": "document_not_found or field_not_found"},
        409: {"description": "document_not_ready: the document is not processed"},
    },
)
def delete_field(document_id: uuid.UUID, field_name: str, service: FieldEditServiceDep) -> Response:
    """Delete a fixed field: the filters and the chat stop using it.

    Args:
        document_id: Document identifier.
        field_name: Field name, for example ``policy_number``.
        service: Field edit service.

    Returns:
        An empty ``204`` response.
    """
    service.delete(document_id, field_name)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
