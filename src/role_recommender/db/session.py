"""
session.py — Async SQLAlchemy session factory.

The engine is created lazily so import-time failures (no DATABASE_URL) are
avoided in local dev without Docker.
"""
from __future__ import annotations

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_engine = None
_SessionLocal = None


def _get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        url = os.environ.get("DATABASE_URL", "")
        if not url:
            raise RuntimeError(
                "DATABASE_URL is not set. "
                "Run inside Docker or set the env var manually."
            )
        _engine = create_async_engine(url, echo=False, pool_pre_ping=True)
        _SessionLocal = async_sessionmaker(
            _engine, expire_on_commit=False, class_=AsyncSession
        )
    return _engine, _SessionLocal


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields one session per request."""
    _, session_factory = _get_engine()
    async with session_factory() as session:
        yield session
