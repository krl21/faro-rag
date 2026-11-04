"""Celery application and worker process setup."""

from celery import Celery
from celery.signals import setup_logging, worker_process_init, worker_process_shutdown

from app.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()

celery_app = Celery("faro", broker=settings.redis_url, include=["app.worker.tasks"])
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_backend=None,
    task_ignore_result=True,
    # Delivery guarantees: acknowledge after the task finishes and requeue it
    # if the worker process dies, giving at-least-once execution. Tasks are
    # idempotent, so a duplicate run is harmless.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    # Must exceed the longest task, or Redis redelivers it while still running.
    broker_transport_options={"visibility_timeout": 3600},
    broker_connection_retry_on_startup=True,
)


@setup_logging.connect
def _configure_worker_logging(**_: object) -> None:
    """Use the JSON logging configuration instead of Celery's default.

    Args:
        **_: Signal arguments (unused).
    """
    configure_logging(settings.log_level)


@worker_process_init.connect
def _init_worker_process(**_: object) -> None:
    """Initialize telemetry and run startup checks in each worker child process.

    Instrumentation must run after the fork, inside every child, so spans
    are exported from the process that executes the tasks. The embedding
    dimension check also loads the model once, before the first task.

    Args:
        **_: Signal arguments (unused).
    """
    from app.ai.providers.factory import get_embedding_provider
    from app.core.startup_checks import check_embedding_dimension, check_pdf_input
    from app.core.telemetry import init_telemetry
    from app.db.session import engine

    # Do not reuse connections inherited from the parent process.
    engine.dispose(close=False)
    init_telemetry(settings, "faro-worker", engine)
    check_embedding_dimension(settings, get_embedding_provider(), engine)
    check_pdf_input(settings)


@worker_process_shutdown.connect
def _shutdown_worker_process(**_: object) -> None:
    """Flush the pending spans before a worker child process exits.

    Args:
        **_: Signal arguments (unused).
    """
    from app.core.telemetry import shutdown_telemetry

    shutdown_telemetry()
