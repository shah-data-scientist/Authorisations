"""
cache.py — Redis helper with graceful parquet fallback.

Usage:
    from role_recommender.cache import get_df, set_df

Both functions are no-ops when REDIS_URL is not set or Redis is unreachable,
so the codebase works identically in local dev (no Redis) and in Docker.
"""
from __future__ import annotations

import io
import os

import pandas as pd

_FLEET_KEY = "fleet_analytics"
_TTL = 86_400  # 24 h


def _client():
    url = os.environ.get("REDIS_URL", "")
    if not url:
        return None
    try:
        import redis

        r = redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
        r.ping()
        return r
    except Exception:
        return None


def get_df(key: str) -> pd.DataFrame | None:
    """Return a DataFrame from Redis, or None if unavailable."""
    c = _client()
    if c is None:
        return None
    try:
        data = c.get(key)
        if data:
            return pd.read_parquet(io.BytesIO(data))
    except Exception:
        pass
    return None


def set_df(key: str, df: pd.DataFrame, ttl: int = _TTL) -> None:
    """Serialize a DataFrame to Redis with a TTL. Silent on failure."""
    c = _client()
    if c is None:
        return
    try:
        buf = io.BytesIO()
        df.to_parquet(buf)
        c.setex(key, ttl, buf.getvalue())
    except Exception:
        pass
