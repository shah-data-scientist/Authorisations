"""
matrix.py — helpers for loading and inspecting the user × permission matrix.
"""
import pandas as pd
from role_recommender.config import PROCESSED_MATRIX


def load_matrix() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_MATRIX)


def matrix_stats(matrix: pd.DataFrame) -> dict:
    n_users, n_resources = matrix.shape
    sparsity = 1 - matrix.values.mean()
    return {
        "n_users": n_users,
        "n_resources": n_resources,
        "sparsity": round(sparsity, 4),
        "density": round(1 - sparsity, 4),
    }
