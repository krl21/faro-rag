"""Document endpoints: upload, list and detail."""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, File, Query, Response, UploadFile, status

from app.api.deps import DocumentServiceDep, SettingsDep
from app.api.mappers import to_detail, to_summary
from app.core.flow_logging import fields
from app.schemas.documents import DocumentDetail, DocumentSummary, DocumentUploadResponse
from app.services.document_service import DUPLICATE_MESSAGE, REQUEUED_MESSAGE
from app.services.file_validation import validate_pdf_upload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        200: {"description": "Duplicate: the document already existed"},
        202: {"description": "Accepted: new document, or failed duplicate queued again"},
    },
)
def upload_document(
    response: Response,
    service: DocumentServiceDep,
    settings: SettingsDep,
    file: Annotated[UploadFile, File(description="PDF file")],
) -> DocumentUploadResponse:
    """Upload a PDF and enqueue its processing.

    Returns immediately with the document id. Processing runs in the worker;
    poll ``GET /documents/{id}`` to follow its status. ``202`` means work was
    queued (a new document, or a duplicate that had failed and is retried);
    ``200`` means nothing was queued because the document already existed.

    Args:
        response: Outgoing response (status set to 200 for duplicates not requeued).
        service: Document service.
        settings: Application settings.
        file: Uploaded file.

    Returns:
        The document id and status. ``duplicate=True`` with a notification
        message when the same content was already uploaded.
    """
    # Sync endpoint: FastAPI runs it in a thread pool, so blocking I/O is fine.
    content = file.file.read(settings.max_upload_bytes + 1)
    filename = validate_pdf_upload(
        file.filename, file.content_type, content, settings.max_upload_bytes
    )
    logger.debug(
        "upload received",
        extra=fields(
            filename=file.filename, content_type=file.content_type, size_bytes=len(content)
        ),
    )
    result = service.upload(filename, content)
    if result.requeued:
        return DocumentUploadResponse(
            id=result.document.id,
            status=result.document.status,
            duplicate=True,
            message=REQUEUED_MESSAGE.format(id=result.document.id),
        )
    if result.duplicate:
        response.status_code = status.HTTP_200_OK
        return DocumentUploadResponse(
            id=result.document.id,
            status=result.document.status,
            duplicate=True,
            message=DUPLICATE_MESSAGE.format(id=result.document.id),
        )
    return DocumentUploadResponse(
        id=result.document.id, status=result.document.status, duplicate=False
    )


@router.get("", response_model=list[DocumentSummary])
def list_documents(
    service: DocumentServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DocumentSummary]:
    """List documents with their status, newest first.

    Args:
        service: Document service.
        limit: Page size.
        offset: Rows to skip.

    Returns:
        The documents.
    """
    logger.debug("document list requested", extra=fields(limit=limit, offset=offset))
    return [to_summary(d) for d in service.list(limit=limit, offset=offset)]


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(document_id: uuid.UUID, service: DocumentServiceDep) -> DocumentDetail:
    """Get a document with its status, extracted fields and errors.

    Args:
        document_id: Document identifier.
        service: Document service.

    Returns:
        The document detail.
    """
    logger.debug("document detail requested", extra=fields(document_id=str(document_id)))
    document, chunk_count = service.get(document_id)
    return to_detail(document, chunk_count)
