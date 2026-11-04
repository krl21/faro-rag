"""Log every HTTP request: the entry point of each flow."""

import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from app.core.flow_logging import fields

logger = logging.getLogger("app.api.requests")

_QUIET_PREFIXES = ("/health",)
"""Polled every few seconds by the UI: logged at DEBUG to avoid noise."""


async def log_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Log the method, path, status and duration of a request.

    ``INFO`` for every request (``DEBUG`` for health checks), ``ERROR`` for
    unhandled exceptions. The query string is logged at ``DEBUG`` only.

    Args:
        request: Incoming request.
        call_next: Next handler.

    Returns:
        The response.
    """
    started = time.perf_counter()
    path = request.url.path
    logger.debug(
        "request received",
        extra=fields(
            method=request.method,
            path=path,
            query=str(request.url.query),
            client=request.client.host if request.client else None,
        ),
    )
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "request failed with an unhandled error",
            extra=fields(method=request.method, path=path, duration_ms=_ms(started)),
        )
        raise
    level = logging.DEBUG if path.startswith(_QUIET_PREFIXES) else logging.INFO
    logger.log(
        level,
        "request handled",
        extra=fields(
            method=request.method,
            path=path,
            status_code=response.status_code,
            duration_ms=_ms(started),
        ),
    )
    return response


def _ms(started: float) -> int:
    """Milliseconds since ``started``.

    Args:
        started: Value of ``time.perf_counter()`` at the start.

    Returns:
        Elapsed time, rounded.
    """
    return round((time.perf_counter() - started) * 1000)
