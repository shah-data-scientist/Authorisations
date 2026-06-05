"""
main.py — FastAPI application entry point.
Run with: uvicorn role_recommender.api.main:app --reload --port 8000
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from role_recommender.api.routers import analytics, drift, roles, users
from role_recommender.api.routers import simulations
from role_recommender.db.session import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create SQLite tables (no-op if they already exist)
    try:
        create_tables()
        logger.info("Audit database: OK")
    except Exception as exc:
        logger.warning(f"Audit database setup failed: {exc}")

    # Warm up fleet analytics in the background
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
