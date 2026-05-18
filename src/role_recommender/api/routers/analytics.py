"""
analytics.py — GET /analytics/fleet and POST /analytics/refresh.

Priority order for reading fleet analytics:
  1. Redis (shared cache, works across container replicas)
  2. Parquet on disk (local dev without Redis)
  3. Compute from scratch and write to Redis / parquet
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, HTTPException

from role_recommender.cache import _FLEET_KEY, get_df, set_df
from role_recommender.config import (
    DATA_PROCESSED,
    MODELS_DIR,
    PROCESSED_MATRIX,
)

router = APIRouter()

_ANALYTICS_PATH: Path = DATA_PROCESSED / "fleet_analytics.parquet"
_MAX_AGE_SECONDS: int = 86_400  # 24 h


def _run_computation() -> pd.DataFrame:
    """Load models; compute fleet analytics; persist to Redis + parquet."""
    from role_recommender.analytics import compute_fleet_analytics
    from role_recommender.mining.probabilistic import ProbabilisticRoleMiner

    model_path = next(MODELS_DIR.glob("role_miner_*.joblib"), None)
    if model_path is None:
        return pd.DataFrame()
    miner = ProbabilisticRoleMiner.load(model_path)

    if not PROCESSED_MATRIX.exists():
        return pd.DataFrame()
    matrix = pd.read_parquet(PROCESSED_MATRIX)

    df = compute_fleet_analytics(miner, matrix)

    # Write to Redis (primary cache in Docker)
    set_df(_FLEET_KEY, df)

    # Write to parquet (fallback for local dev; silently skip if read-only)
    try:
        _ANALYTICS_PATH.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(_ANALYTICS_PATH, index=False)
    except OSError:
        pass

    return df


def _load_analytics() -> pd.DataFrame | None:
    """Try Redis → parquet. Return None if neither is available/fresh."""
    # 1. Redis
    df = get_df(_FLEET_KEY)
    if df is not None:
        return df

    # 2. Parquet (local dev)
    if _ANALYTICS_PATH.exists():
        age = time.time() - _ANALYTICS_PATH.stat().st_mtime
        if age < _MAX_AGE_SECONDS:
            return pd.read_parquet(_ANALYTICS_PATH)

    return None


def ensure_analytics_fresh() -> None:
    """Called at API startup: compute analytics if not in Redis or parquet."""
    if _load_analytics() is None:
        _run_computation()


@router.get(
    "/fleet",
    summary="Return pre-computed fleet analytics for all employees",
)
def get_fleet_analytics():
    df = _load_analytics()
    if df is None or df.empty:
        raise HTTPException(
            status_code=503,
            detail=(
                "Fleet analytics not yet computed. "
                "Call POST /analytics/refresh or open the dashboard first."
            ),
        )
    return df.to_dict(orient="records")


@router.post(
    "/refresh",
    summary="Trigger background recomputation of fleet analytics",
)
def refresh_analytics(background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_computation)
    return {
        "status": "refresh triggered",
        "message": "Analytics will be ready shortly.",
    }
