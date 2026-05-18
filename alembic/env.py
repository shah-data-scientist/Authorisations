"""
alembic/env.py — Alembic migration environment.

Uses a synchronous psycopg2 connection for migrations (asyncpg is async-only
and cannot be used directly by Alembic). The DATABASE_URL env var is expected
in asyncpg format (postgresql+asyncpg://...); this file converts it to psycopg2.
"""
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import ORM metadata so Alembic can autogenerate migrations
from role_recommender.db.models import Base  # noqa: E402

target_metadata = Base.metadata


def _sync_url() -> str:
    url = os.environ.get("DATABASE_URL", config.get_main_option("sqlalchemy.url", ""))
    # Alembic uses psycopg2 (sync); replace the asyncpg driver
    return (
        url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        .replace("postgresql://", "postgresql+psycopg2://")
    )


def run_migrations_offline() -> None:
    context.configure(
        url=_sync_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = _sync_url()
    connectable = engine_from_config(cfg, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
