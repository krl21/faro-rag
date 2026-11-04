"""Synchronous validation of uploaded files (type and size)."""

import logging
from pathlib import PurePath

from app.core.errors import EmptyFileError, FaroError, FileTooLargeError, InvalidFileTypeError
from app.core.flow_logging import fields

logger = logging.getLogger(__name__)

PDF_MAGIC = b"%PDF-"
ALLOWED_CONTENT_TYPES = frozenset(
    {"application/pdf", "application/x-pdf", "application/octet-stream"}
)


def validate_pdf_upload(
    filename: str | None,
    content_type: str | None,
    content: bytes,
    max_bytes: int,
) -> str:
    """Check that an upload looks like a PDF within the size limit.

    The file signature is checked, not only the extension or the declared
    content type, which the client controls. Deeper checks (corrupt
    structure, page count, missing text) happen in the worker.

    Args:
        filename: Client-provided filename.
        content_type: Client-provided MIME type.
        content: File bytes (read up to ``max_bytes + 1``).
        max_bytes: Maximum accepted size.

    Returns:
        A safe filename (directory parts removed).

    Raises:
        EmptyFileError: If the file is empty.
        FileTooLargeError: If the file exceeds ``max_bytes``.
        InvalidFileTypeError: If the extension, MIME type or signature is not PDF.
    """
    try:
        safe_name = _check(filename, content_type, content, max_bytes)
    except FaroError as exc:
        logger.warning(
            "upload rejected",
            extra=fields(
                reason=exc.code,
                error=exc.message,
                filename=filename,
                content_type=content_type,
                size_bytes=len(content),
            ),
        )
        raise
    logger.info("upload validated", extra=fields(filename=safe_name, size_bytes=len(content)))
    return safe_name


def _check(filename: str | None, content_type: str | None, content: bytes, max_bytes: int) -> str:
    """Run the upload checks; see ``validate_pdf_upload``.

    Args:
        filename: Client-provided filename.
        content_type: Client-provided MIME type.
        content: File bytes.
        max_bytes: Maximum accepted size.

    Returns:
        The safe filename.

    Raises:
        EmptyFileError: If the file is empty.
        FileTooLargeError: If the file exceeds ``max_bytes``.
        InvalidFileTypeError: If the extension, MIME type or signature is not PDF.
    """
    if not content:
        raise EmptyFileError("The uploaded file is empty")
    if len(content) > max_bytes:
        raise FileTooLargeError(f"The file exceeds the {max_bytes // (1024 * 1024)} MB limit")

    safe_name = PurePath(filename or "document.pdf").name[:255] or "document.pdf"
    if not safe_name.lower().endswith(".pdf"):
        raise InvalidFileTypeError("Only .pdf files are accepted")
    if content_type and content_type.split(";")[0].strip().lower() not in ALLOWED_CONTENT_TYPES:
        raise InvalidFileTypeError(f"Unsupported content type: {content_type}")
    if not content.lstrip()[:1024].startswith(PDF_MAGIC):
        raise InvalidFileTypeError("The file content is not a PDF")
    return safe_name
