"""Helpers to log each step of a flow with the same shape.

Convention used across the backend:

- ``INFO``: a step finished, with ids, counters and its duration
  (``"document classified"``, ``document_id``, ``document_type``, ``duration_ms``).
- ``DEBUG``: the full detail of the step's input and output (question, filters,
  document text, LLM answer). Enabled with ``LOG_LEVEL=DEBUG``.
- ``WARNING``: something went wrong but the flow continues (an invalid LLM
  answer that will be retried, a rejected upload).
- ``ERROR``: the step failed for good.

Never log PDF bytes or credentials. Every line carries the ``trace_id`` of the
request or task (see ``app.core.logging``), so it can be matched in Jaeger.
"""

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

# LogRecord attributes: an ``extra`` key with one of these names makes
# ``logging`` raise, so such keys are renamed with a ``field_`` prefix.
_RESERVED = frozenset(vars(logging.makeLogRecord({})).keys()) | {"message", "asctime"}


def fields(**values: Any) -> dict[str, Any]:
    """Build a safe ``extra`` dictionary for a log call.

    Args:
        **values: Fields to attach to the log line.

    Returns:
        The fields, with names that clash with ``LogRecord`` attributes
        (``filename``, ``name``, ``module``...) prefixed with ``field_``.
    """
    return {(f"field_{k}" if k in _RESERVED else k): v for k, v in values.items()}


@contextmanager
def log_step(logger: logging.Logger, step: str, **inputs: Any) -> Iterator[dict[str, Any]]:
    """Log the start (DEBUG), end (INFO) or failure (WARNING) of a step, with its duration.

    Usage::

        with log_step(logger, "document classified", document_id=doc_id) as out:
            out["document_type"] = classify(...)

    Args:
        logger: Logger of the module running the step.
        step: Message logged when the step finishes, for example
            ``"document classified"``.
        **inputs: Fields logged with every line of the step (ids, counters).

    Yields:
        A dictionary the step fills with its outputs; they are added to the
        ``INFO`` line.

    Raises:
        Exception: Whatever the step raises, after logging it.
    """
    outputs: dict[str, Any] = {}
    logger.debug(f"{step}: started", extra=fields(step=step, **inputs))
    started = time.perf_counter()
    try:
        yield outputs
    except Exception as exc:
        logger.warning(
            f"{step}: failed",
            extra=fields(
                step=step,
                duration_ms=_elapsed_ms(started),
                error_type=type(exc).__name__,
                error=str(exc),
                **inputs,
            ),
        )
        raise
    logger.info(
        step, extra=fields(step=step, duration_ms=_elapsed_ms(started), **inputs, **outputs)
    )


def _elapsed_ms(started: float) -> int:
    """Milliseconds since ``started``.

    Args:
        started: Value of ``time.perf_counter()`` at the start.

    Returns:
        Elapsed time, rounded.
    """
    return round((time.perf_counter() - started) * 1000)
