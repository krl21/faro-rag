"""OpenTelemetry setup for the API and the Celery worker."""

import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from sqlalchemy.engine import Engine

from app.config import Settings

logger = logging.getLogger(__name__)

TRACER_NAME = "faro-rag"


def get_tracer() -> trace.Tracer:
    """Return the tracer used for the application's manual spans.

    Returns:
        An OpenTelemetry tracer.
    """
    return trace.get_tracer(TRACER_NAME)


def init_telemetry(settings: Settings, service_name: str, engine: Engine) -> None:
    """Configure tracing and instrument the shared libraries.

    Instruments SQLAlchemy, Redis and Celery. Celery instrumentation injects
    the trace context into task headers when a task is sent, and restores it
    in the worker, so one trace spans the HTTP request and the task. FastAPI
    is instrumented separately in ``app.main`` because it needs the app.

    Args:
        settings: Application settings.
        service_name: Name shown in the trace viewer (``faro-api`` or ``faro-worker``).
        engine: SQLAlchemy engine to instrument.
    """
    if not settings.otel_enabled:
        logger.info("telemetry disabled")
        return

    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: service_name}))
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)
        )
    )
    trace.set_tracer_provider(provider)

    SQLAlchemyInstrumentor().instrument(engine=engine)
    RedisInstrumentor().instrument()
    CeleryInstrumentor().instrument()
    logger.info("telemetry enabled", extra={"service": service_name})


def shutdown_telemetry(provider: trace.TracerProvider | None = None) -> None:
    """Export the pending spans and stop the exporter.

    ``BatchSpanProcessor`` sends spans in batches every few seconds. Without
    this call, the spans still queued when a process stops (a worker restart,
    a redeploy) are lost, usually the trace of the last request or task.

    Args:
        provider: Provider to shut down; defaults to the global one. Does
            nothing when telemetry is disabled (no SDK provider configured).
    """
    provider = provider or trace.get_tracer_provider()
    shutdown = getattr(provider, "shutdown", None)
    if callable(shutdown):
        shutdown()
        logger.info("telemetry flushed and shut down")
