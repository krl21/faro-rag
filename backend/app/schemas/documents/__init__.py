"""Request and response models for the ``/documents`` endpoints.

One module per class; this package re-exports the public names.
"""

from app.schemas.documents.document_detail import DocumentDetail
from app.schemas.documents.document_error import DocumentError
from app.schemas.documents.document_fact_out import DocumentFactOut
from app.schemas.documents.document_summary import DocumentSummary
from app.schemas.documents.document_upload_response import DocumentUploadResponse
from app.schemas.documents.extracted_field_out import ExtractedFieldOut
from app.schemas.documents.fact_update_request import FactUpdateRequest
from app.schemas.documents.field_update_request import FieldUpdateRequest

__all__ = [
    "DocumentDetail",
    "DocumentError",
    "DocumentFactOut",
    "DocumentSummary",
    "DocumentUploadResponse",
    "ExtractedFieldOut",
    "FactUpdateRequest",
    "FieldUpdateRequest",
]
