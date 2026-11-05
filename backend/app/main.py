"""FastAPI entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.ai.providers.factory import get_embedding_provider
from app.api.request_logging import log_requests
from app.api.routes import (
    ask,
    conversations,
    document_ask,
    document_facts,
    document_fields,
    documents,
    health,
)
from app.config import get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.core.rate_limit import limiter
from app.core.startup_checks import check_embedding_dimension
from app.core.telemetry import init_telemetry, shutdown_telemetry
from app.db.session import engine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Run startup checks before serving requests and flush spans on shutdown.

    Args:
        _: The application.

    Yields:
        Control back to FastAPI while the app runs.
    """
    check_embedding_dimension(get_settings(), get_embedding_provider(), engine)
    yield
    shutdown_telemetry()


def create_app() -> FastAPI:
    """Build the FastAPI application.

    Returns:
        The configured application.
    """
    settings = get_settings()
    configure_logging(settings.log_level)
    init_telemetry(settings, "faro-api", engine)

    app = FastAPI(title="Faro RAG API", version="0.1.0", lifespan=lifespan)
    app.state.limiter = limiter
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.middleware("http")(log_requests)
    app.include_router(health.router)
    app.include_router(documents.router)
    app.include_router(document_fields.router)
    app.include_router(document_facts.router)
    app.include_router(document_ask.router)
    app.include_router(ask.router)
    app.include_router(conversations.router)

    if settings.otel_enabled:
        FastAPIInstrumentor.instrument_app(app, excluded_urls="health")
    return app


app = create_app()
