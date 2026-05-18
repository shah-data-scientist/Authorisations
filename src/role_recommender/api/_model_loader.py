"""
_model_loader.py — singleton loader for the trained miner, matrix, and scorer.
Imported by all routers; model is loaded once at first request.
"""
from functools import lru_cache
from fastapi import HTTPException
import pandas as pd
from role_recommender.config import MODELS_DIR, PROCESSED_MATRIX
from role_recommender.mining.probabilistic import ProbabilisticRoleMiner
from role_recommender.drift.scorer import DriftScorer


@lru_cache(maxsize=1)
def get_miner() -> ProbabilisticRoleMiner:
    path = next(MODELS_DIR.glob("role_miner_*.joblib"), None)
    if path is None:
        raise HTTPException(
            status_code=503,
            detail="Role model not found. Run `make train` first.",
        )
    return ProbabilisticRoleMiner.load(path)


@lru_cache(maxsize=1)
def get_matrix() -> pd.DataFrame:
    if not PROCESSED_MATRIX.exists():
        raise HTTPException(
            status_code=503,
            detail="Processed matrix not found. Run `make data` first.",
        )
    return pd.read_parquet(PROCESSED_MATRIX)


@lru_cache(maxsize=1)
def get_scorer() -> DriftScorer:
    return DriftScorer(get_miner())
