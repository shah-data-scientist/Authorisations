"""
main.py — FastAPI application entry point.
Run with: uvicorn role_recommender.api.main:app --reload --port 8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from role_recommender.api.routers import analytics, drift, roles, users
from role_recommender.api.routers import simulations


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    import os

    # DB connection check (non-fatal)
    if os.environ.get("DATABASE_URL"):
        try:
            from sqlalchemy import text
            from role_recommender.db.session import _get_engine
            engine, _ = _get_engine()
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Database connection: OK")
        except Exception as exc:
            logger.warning(
                f"Database not reachable: {exc}. "
                "Simulation persistence disabled."
            )

    # Kick off fleet analytics in the background so /health responds immediately.
    # The dashboard and /analytics/fleet will block until it's ready via Redis/parquet.
    asyncio.create_task(
        asyncio.to_thread(analytics.ensure_analytics_fresh)
    )

    yield


app = FastAPI(
    title="Access Management Platform API",
    description=(
        "Hybrid role mining + access drift detection "
        "on the Amazon Employee Access dataset."
    ),
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(roles.router, prefix="/roles", tags=["Roles"])
app.include_router(drift.router, prefix="/drift", tags=["Drift"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(
    simulations.router, prefix="/simulations", tags=["Simulations"]
)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
