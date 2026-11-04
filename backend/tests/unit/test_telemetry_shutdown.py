"""Pending spans are exported when a process stops."""

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import NoOpTracerProvider

from app.core import telemetry
from app.core.telemetry import shutdown_telemetry
from app.worker import celery_app


def _batched_provider() -> tuple[TracerProvider, InMemorySpanExporter]:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    # Long delay: without a flush the span would still be queued.
    provider.add_span_processor(BatchSpanProcessor(exporter, schedule_delay_millis=60_000))
    return provider, exporter


def test_queued_spans_are_lost_without_shutdown():
    provider, exporter = _batched_provider()
    with provider.get_tracer("test").start_as_current_span("ingest.embed"):
        pass
    assert exporter.get_finished_spans() == ()


def test_shutdown_exports_queued_spans():
    provider, exporter = _batched_provider()
    with provider.get_tracer("test").start_as_current_span("ingest.embed"):
        pass
    shutdown_telemetry(provider)
    assert [s.name for s in exporter.get_finished_spans()] == ["ingest.embed"]


def test_shutdown_is_a_no_op_when_telemetry_is_disabled():
    shutdown_telemetry(NoOpTracerProvider())  # No SDK provider: nothing to flush, no error.


def test_worker_child_flushes_on_exit(monkeypatch):
    calls = []
    monkeypatch.setattr(telemetry, "shutdown_telemetry", lambda: calls.append("flush"))
    celery_app._shutdown_worker_process()
    assert calls == ["flush"]
