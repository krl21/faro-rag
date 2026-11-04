"""Domain exceptions shared by the API, the worker and the AI layer."""


class FaroError(Exception):
    """Base class for every domain error.

    Attributes:
        code: Stable machine-readable error code exposed by the API.
        status_code: HTTP status used when the error reaches the API.
    """

    code: str = "internal_error"
    status_code: int = 500

    def __init__(self, message: str) -> None:
        """Create the error.

        Args:
            message: Human-readable description of the problem.
        """
        super().__init__(message)
        self.message = message


# --- Upload validation (rejected synchronously by the API) ---


class InvalidFileTypeError(FaroError):
    """The uploaded file is not a PDF."""

    code = "invalid_file_type"
    status_code = 415


class FileTooLargeError(FaroError):
    """The uploaded file exceeds the configured size limit."""

    code = "file_too_large"
    status_code = 413


class EmptyFileError(FaroError):
    """The uploaded file has no content."""

    code = "empty_file"
    status_code = 400


class DocumentNotFoundError(FaroError):
    """The requested document does not exist."""

    code = "document_not_found"
    status_code = 404


class ConversationNotFoundError(FaroError):
    """The requested conversation does not exist."""

    code = "conversation_not_found"
    status_code = 404


class DocumentNotReadyError(FaroError):
    """The document is not processed yet (or failed), so the action is not possible."""

    code = "document_not_ready"
    status_code = 409


class FieldNotFoundError(FaroError):
    """The document type has no field with that name, or it cannot be edited."""

    code = "field_not_found"
    status_code = 404


class InvalidFieldValueError(FaroError):
    """The value sent for a field does not have the expected shape."""

    code = "invalid_field_value"
    status_code = 422


class QueueUnavailableError(FaroError):
    """The processing task could not be sent to the broker."""

    code = "queue_unavailable"
    status_code = 503


# --- Processing errors (permanent: retrying will not help) ---


class PermanentProcessingError(FaroError):
    """Processing failed for a reason that a retry cannot fix."""

    code = "processing_failed"
    status_code = 422


class CorruptPdfError(PermanentProcessingError):
    """The PDF cannot be parsed."""

    code = "corrupt_pdf"


class NoExtractableTextError(PermanentProcessingError):
    """The PDF has no extractable text (for example, a scanned document)."""

    code = "no_extractable_text"


class TooManyPagesError(PermanentProcessingError):
    """The PDF exceeds the configured page limit."""

    code = "too_many_pages"


class ExtractorUnavailableError(PermanentProcessingError):
    """The configured PDF extractor is not installed in this image."""

    code = "extractor_unavailable"


# --- Provider errors (transient: worth retrying) ---


class ProviderError(FaroError):
    """An LLM or embedding provider call failed."""

    code = "provider_error"
    status_code = 502


class ProviderTimeoutError(ProviderError):
    """An LLM or embedding provider call exceeded its timeout."""

    code = "provider_timeout"
    status_code = 504


class EmbeddingDimensionError(FaroError):
    """The embedding provider returns vectors of an unexpected dimension."""

    code = "embedding_dimension_mismatch"
    status_code = 500
