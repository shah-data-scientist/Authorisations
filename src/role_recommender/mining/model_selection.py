"""
model_selection.py — BIC / elbow analysis to select the optimal number of roles.

Usage:
    python -m role_recommender.mining.model_selection
Outputs a CSV of (k, reconstruction_error, bic) to models/model_selection.csv
and logs the recommended k.
"""
import numpy as np
import pandas as pd
from loguru import logger
from role_recommender.config import (
    PROCESSED_MATRIX, MODELS_DIR,
    ROLE_COUNT_MIN, ROLE_COUNT_MAX, RANDOM_STATE,
)
from role_recommender.mining.probabilistic import ProbabilisticRoleMiner

CANDIDATE_K = [5, 7, 10, 12, 15, 20, 25, 30]


def bic(reconstruction_err: float, n_users: int, n_resources: int, k: int) -> float:
    """
    Approximate BIC for NMF: penalises model complexity (k × (n_users + n_resources)).
    Lower is better.
    """
    n_params = k * (n_users + n_resources)
    n_obs = n_users * n_resources
    # BIC = n_obs * log(MSE) + n_params * log(n_obs)
    mse = (reconstruction_err ** 2) / n_obs
    return n_obs * np.log(mse + 1e-10) + n_params * np.log(n_obs)


def run_selection(
    candidate_k: list[int] = CANDIDATE_K,
) -> pd.DataFrame:
    matrix = pd.read_parquet(PROCESSED_MATRIX)
    n_users, n_resources = matrix.shape
    logger.info(f"Matrix: {n_users} users × {n_resources} resources")

    records = []
    for k in candidate_k:
        logger.info(f"Fitting NMF with k={k} …")
        miner = ProbabilisticRoleMiner(n_roles=k, random_state=RANDOM_STATE)
        miner.fit(matrix)
        err = miner.reconstruction_error()
        b = bic(err, n_users, n_resources, k)
        records.append({"k": k, "reconstruction_error": err, "bic": b})
        logger.info(f"  k={k:>2}  err={err:.4f}  BIC={b:.2f}")

    df = pd.DataFrame(records)

    # Recommend the k with lowest BIC
    best_k = int(df.loc[df["bic"].idxmin(), "k"])
    logger.success(f"Recommended k by BIC: {best_k}")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    out = MODELS_DIR / "model_selection.csv"
    df.to_csv(out, index=False)
    logger.info(f"Results saved → {out}")
    return df


if __name__ == "__main__":
    run_selection()
