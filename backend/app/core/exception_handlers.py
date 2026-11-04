"""Map domain exceptions to JSON HTTP responses."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.core.errors import FaroError

logger = logging.getLogger(__name__)


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    """Build the standard error body.

    Args:
        status_code: HTTP status.
        code: Machine-readable error code.
        message: Description.

    Returns:
        ``{"error": {"code": ..., "message": ...}}``.
    """
    return JSONResponse(
        status_code=status_code, content={"error": {"code": code, "message": message}}
    )


async def _handle_domain_error(_: Request, exc: Exception) -> JSONResponse:
    """Return a domain error with its own status and code.

    Args:
        _: Incoming request.
        exc: The raised ``FaroError``.

    Returns:
        The JSON error response.
    """
    if not isinstance(exc, FaroError):  # pragma: no cover - registered for FaroError only
        raise exc
    if exc.status_code >= 500:
        logger.error("request failed", extra={"error_code": exc.code, "error": exc.message})
    return _error_response(exc.status_code, exc.code, exc.message)


async def _handle_rate_limit(_: Request, exc: Exception) -> JSONResponse:
    """Return 429 when a client exceeds the rate limit.

    Args:
        _: Incoming request.
        exc: The raised ``RateLimitExceeded``.

    Returns:
        The JSON error response.
    """
    return _error_response(429, "rate_limited", f"Rate limit exceeded: {exc}")


def register_exception_handlers(app: FastAPI) -> None:
    """Attach the handlers to the application.

    Args:
        app: FastAPI application.
    """
    app.add_exception_handler(FaroError, _handle_domain_error)
    app.add_exception_handler(RateLimitExceeded, _handle_rate_limit)
