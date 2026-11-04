"""Liveness and readiness endpoints."""

import logging

import redis
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.api.deps import SessionDep, SettingsDep

router = APIRouter(prefix="/health", tags=["health"])
logger = logging.getLogger(__name__)


@router.get("")
def liveness() -> dict[str, str]:
    """Report that the process is running.

    Returns:
        ``{"status": "ok"}``.
    """
    return {"status": "ok"}


@router.get("/ready")
def readiness(response: Response, session: SessionDep, settings: SettingsDep) -> dict[str, str]:
    """Check the database, Redis and that at least one Celery worker answers.

    Args:
        response: Outgoing response (status set to 503 when not ready).
        session: Database session.
        settings: Application settings.

    Returns:
        The status of each dependency.
    """
    checks: dict[str, str] = {}
    try:
        session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        logger.warning("database not ready", extra={"error": str(exc)})
        checks["database"] = "error"
    try:
        redis.Redis.from_url(settings.redis_url, socket_timeout=2).ping()
        checks["redis"] = "ok"
    except Exception as exc:
        logger.warning("redis not ready", extra={"error": str(exc)})
        checks["redis"] = "error"
    checks["worker"] = "ok" if checks["redis"] == "ok" and _worker_alive() else "error"
    if any(value != "ok" for value in checks.values()):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return checks


def _worker_alive() -> bool:
    """Ping the Celery workers through the broker.

    Returns:
        ``True`` if at least one worker replied within one second.
    """
    from app.worker.celery_app import celery_app

    try:
        replies = celery_app.control.ping(timeout=1)
    except Exception as exc:
        logger.warning("worker ping failed", extra={"error": str(exc)})
        return False
    if not replies:
        logger.warning("no worker replied to the ping")
    return bool(replies)
