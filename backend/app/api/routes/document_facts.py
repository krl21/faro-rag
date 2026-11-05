"""Edition and deletion of the free label-value data of a document by the user."""

import logging
import uuid

from fastapi import APIRouter, Response, status

from app.api.deps import FactEditServiceDep
from app.api.mappers import to_fact_out
from app.core.flow_logging import fields
from app.schemas.documents import DocumentFactOut, FactUpdateRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

_ERRORS = {
    404: {"description": "document_not_found or fact_not_found"},
    409: {"description": "document_not_ready: the document is not processed"},
}


@router.patch(
    "/{document_id}/facts/{fact_id}",
    response_model=DocumentFactOut,
    responses={
        **_ERRORS,
        422: {"description": "invalid_fact_value: empty or too long label or value"},
    },
)
def update_fact(
    document_id: uuid.UUID,
    fact_id: int,
    body: FactUpdateRequest,
    service: FactEditServiceDep,
) -> DocumentFactOut:
    """Correct the label and/or the value of a datum (status becomes ``edited``).

    The datum as found is kept in ``original_value``; the chat uses the new one.

    Args:
        document_id: Document identifier.
        fact_id: Datum identifier (``facts[].id`` of ``GET /documents/{id}``).
        body: New label and/or value.
        service: Datum edit service.

    Returns:
        The updated datum.
    """
    logger.debug(
        "document datum edit received",
        extra=fields(
            document_id=str(document_id), fact_id=fact_id, label=body.label, value=body.value
        ),
    )
    fact = service.edit(document_id, fact_id, label=body.label, value=body.value)
    return to_fact_out(fact)


@router.delete(
    "/{document_id}/facts/{fact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_ERRORS,
)
def delete_fact(document_id: uuid.UUID, fact_id: int, service: FactEditServiceDep) -> Response:
    """Delete a datum: the chat stops using it.

    Args:
        document_id: Document identifier.
        fact_id: Datum identifier.
        service: Datum edit service.

    Returns:
        An empty ``204`` response.
    """
    service.delete(document_id, fact_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
