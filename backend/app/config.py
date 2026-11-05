"""Typed application settings loaded from environment variables."""

from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.domain.enums import (
    DocumentInput,
    EmbeddingProviderName,
    LLMProviderName,
)


class Settings(BaseSettings):
    """Application settings.

    Every attribute maps to an upper-case environment variable with the same
    name (for example ``chunk_size`` -> ``CHUNK_SIZE``).
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- General ---
    app_name: str = "faro-rag"
    log_level: str = "INFO"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # --- Infrastructure ---
    database_url: str = "postgresql+psycopg://faro:faro@postgres:5432/faro"
    redis_url: str = "redis://redis:6379/0"
    storage_dir: str = "/data/uploads"

    # --- Upload limits ---
    max_upload_mb: int = Field(default=20, gt=0)
    max_pages: int = Field(default=200, gt=0)

    # --- Ingestion ---
    chunk_size: int = Field(default=1000, gt=0)
    chunk_overlap: int = Field(default=150, ge=0)

    # --- LLM ---
    llm_provider: LLMProviderName = LLMProviderName.FAKE
    llm_model: str = "fake-llm"
    llm_api_key: str | None = None
    llm_api_base: str | None = None
    llm_timeout_seconds: float = Field(default=20, gt=0)
    llm_temperature: float = Field(default=0.0, ge=0, le=2)

    # --- Embeddings ---
    embedding_provider: EmbeddingProviderName = EmbeddingProviderName.SENTENCE_TRANSFORMERS
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dim: int = Field(default=384, gt=0)
    embedding_api_key: str | None = None
    embedding_api_base: str | None = None
    embedding_timeout_seconds: float = Field(default=10, gt=0)
    embedding_batch_size: int = Field(default=32, gt=0)

    # --- Structured extraction ---
    extraction_retry_delays: list[float] = Field(default_factory=lambda: [2.0, 6.0])
    # What both LLM calls (classification and field extraction) receive as the
    # document: the original PDF (needs a model with PDF input) or its text.
    llm_document_input: DocumentInput = DocumentInput.PDF
    # Only with LLM_DOCUMENT_INPUT=text: text characters sent to classify.
    # Field extraction always gets the whole document.
    classification_max_chars: int = Field(default=12000, gt=0)

    # --- Retrieval (RAG) ---
    retrieval_top_k: int = Field(default=6, gt=0)
    retrieval_candidates: int = Field(default=20, gt=0)
    retrieval_min_similarity: float = Field(default=0.35, ge=0, le=1)
    retrieval_rrf_k: int = Field(default=60, gt=0)
    retrieval_facts_top_k: int = Field(default=15, ge=0, le=100)

    # --- Chat ---
    # IANA zone used to resolve "hoy", "ayer"... (America/Toronto: UTC-5, UTC-4 in summer).
    timezone: str = "America/Toronto"
    # Previous exchanges (question + answer) sent as context to interpret a question.
    chat_context_turns: int = Field(default=3, ge=0, le=10)
    # Maximum documents returned when a question only lists documents.
    chat_list_limit: int = Field(default=50, gt=0, le=500)

    # --- Celery task ---
    # Worker processes running in parallel (documents processed at the same time).
    worker_concurrency: int = Field(default=2, ge=1, le=16)
    task_max_retries: int = Field(default=3, ge=0)
    task_retry_backoff_seconds: int = Field(default=5, gt=0)
    task_retry_backoff_max_seconds: int = Field(default=60, gt=0)

    # --- Rate limiting ---
    ask_rate_limit: str = "10/minute"

    # --- OpenTelemetry ---
    otel_enabled: bool = True
    otel_exporter_otlp_endpoint: str = "http://otel-collector:4317"

    @field_validator("chunk_overlap")
    @classmethod
    def _overlap_smaller_than_size(cls, value: int, info) -> int:
        """Ensure the chunk overlap is smaller than the chunk size.

        Args:
            value: Configured overlap.
            info: Validation context with the already validated fields.

        Returns:
            The validated overlap.

        Raises:
            ValueError: If the overlap is greater than or equal to the chunk size.
        """
        size = info.data.get("chunk_size")
        if size is not None and value >= size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        return value

    @field_validator("timezone")
    @classmethod
    def _known_timezone(cls, value: str) -> str:
        """Ensure the time zone exists in the IANA database.

        Args:
            value: Configured zone name.

        Returns:
            The validated name.

        Raises:
            ValueError: If the zone is unknown.
        """
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"Unknown TIMEZONE {value!r}: use an IANA name") from exc
        return value

    @property
    def tzinfo(self) -> ZoneInfo:
        """Time zone used to interpret dates in questions.

        Returns:
            The ``ZoneInfo`` for ``timezone``.
        """
        return ZoneInfo(self.timezone)

    @property
    def max_upload_bytes(self) -> int:
        """Maximum accepted upload size in bytes.

        Returns:
            ``max_upload_mb`` converted to bytes.
        """
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance.

    Returns:
        The process-wide ``Settings`` object.
    """
    return Settings()
