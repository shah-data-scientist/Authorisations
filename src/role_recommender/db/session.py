"""
session.py — Sync SQLAlchemy session factory (SQLite).

SQLite requires no external service — the DB file is created automatically
inside data/processed/ on first startup.
"""
from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from role_recommender.config import AUDIT_DB

_engine = None
_SessionLocal = None


def _get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        AUDIT_DB.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            f"sqlite:///{AUDIT_DB}",
            connect_args={"check_same_thread": False},
            echo=False,
        )

        @event.listens_for(_engine, "connect")
        def _set_wal(dbapi_conn, _):
            dbapi_conn.execute("PRAGMA journal_mode=WAL")

        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine, _SessionLocal


def create_tables() -> None:
    """Create all ORM tables if they don't exist. Called at API startup."""
    from role_recommender.db.models import Base
    engine, _ = _get_engine()
    Base.metadata.create_all(engine)


def get_session():
    """FastAPI dependency that yields one sync session per request."""
    _, session_factory = _get_engine()
    session: Session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
