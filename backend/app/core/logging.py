"""Structured JSON logging correlated with OpenTelemetry traces."""

import json
import logging
import sys
from datetime import UTC, datetime

from opentelemetry import trace

# Attributes every LogRecord has; anything else was passed through ``extra``.
_STANDARD_ATTRS = frozenset(vars(logging.makeLogRecord({})).keys()) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    """Format log records as one JSON object per line.

    Each line includes the active ``trace_id`` and ``span_id`` so logs can be
    matched with the trace shown in the trace viewer.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Serialize a log record.

        Args:
            record: The record to format.

        Returns:
            The record as a JSON string.
        """
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        span_context = trace.get_current_span().get_span_context()
        if span_context.is_valid:
            payload["trace_id"] = format(span_context.trace_id, "032x")
            payload["span_id"] = format(span_context.span_id, "016x")
        for key, value in vars(record).items():
            if key not in _STANDARD_ATTRS:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: str) -> None:
    """Send every log record to stdout as JSON.

    Args:
        level: Minimum log level name (for example ``"INFO"``).
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    # Silence noisy third-party loggers.
    for name in ("httpx", "LiteLLM", "sentence_transformers"):
        logging.getLogger(name).setLevel(logging.WARNING)
