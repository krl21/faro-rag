"""Per-client rate limiting backed by Redis."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=get_settings().redis_url,
    strategy="fixed-window",
)
"""Shared limiter. Counters live in Redis so every API replica shares them."""
