"""
cluster_utils.py — shared data loading and cluster naming for the dashboard.

Clusters are named A–O (indices 0–14).
All heavy computations are cached so page switches are instant.
"""
import time

import numpy as np
import pandas as pd
import streamlit as st

N_CLUSTERS = 15
CLUSTER_LABELS = [chr(65 + i) for i in range(N_CLUSTERS)]  # ['A'…'O']
STRENGTH_ORDER = ["Strong (>70%)", "Partial (30–70%)", "Weak (<30%)"]
STRENGTH_COLORS = {
    "Strong (>70%)": "#27ae60",
    "Partial (30–70%)": "#f39c12",
    "Weak (<30%)": "#e74c3c",
}
RISK_COLORS = {
    "High": "#e74c3c",
    "Medium": "#f39c12",
    "Low": "#27ae60",
}


def cluster_name(i: int) -> str:
    return chr(65 + i)


# ---------------------------------------------------------------------------
# Resource loaders — @st.cache_resource avoids serialisation of large objects
# ---------------------------------------------------------------------------

@st.cache_resource
def load_miner():
    from role_recommender.mining.probabilistic import ProbabilisticRoleMiner
    from role_recommender.config import MODELS_DIR
    path = next(MODELS_DIR.glob("role_miner_*.joblib"))
    return ProbabilisticRoleMiner.load(path)


@st.cache_resource
def load_matrix():
    from role_recommender.config import PROCESSED_MATRIX
    return pd.read_parquet(PROCESSED_MATRIX)


# ---------------------------------------------------------------------------
# Fleet analytics — Redis → parquet → compute (24 h TTL)
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def load_fleet_analytics() -> pd.DataFrame:
    """
    Load pre-computed fleet analytics. Priority:
      1. Redis (shared cache across Docker replicas)
      2. Parquet on disk (local dev without Redis)
      3. Compute from scratch (~30 s) and write to Redis + parquet
    """
    from role_recommender.analytics import compute_fleet_analytics
    from role_recommender.cache import _FLEET_KEY, get_df, set_df
    from role_recommender.config import DATA_PROCESSED

    analytics_path = DATA_PROCESSED / "fleet_analytics.parquet"

    # 1. Redis
    df = get_df(_FLEET_KEY)
    if df is not None:
        return df

    # 2. Parquet (local dev)
    if analytics_path.exists():
        age = time.time() - analytics_path.stat().st_mtime
        if age < 86_400:
            df = pd.read_parquet(analytics_path)
            set_df(_FLEET_KEY, df)   # warm Redis for next request
            return df

    # 3. Compute from scratch
    df = compute_fleet_analytics(load_miner(), load_matrix())
    set_df(_FLEET_KEY, df)
    try:
        analytics_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(analytics_path, index=False)
    except OSError:
        pass
    return df


# ---------------------------------------------------------------------------
# Fleet-level computations (used by Access Intelligence charts 1-3)
# ---------------------------------------------------------------------------

@st.cache_data
def compute_fleet_stats() -> pd.DataFrame:
    """One row per employee: dominant cluster, weight, strength band."""
    miner = load_miner()
    matrix = load_matrix()
    rows = []
    for user_id in matrix.index:
        weights = miner.get_user_role_weights(user_id)
        dom_idx = int(np.argmax(weights))
        dom_w = float(weights[dom_idx])

        def band(w):
            if w > 0.7:
                return "Strong (>70%)"
            if w >= 0.3:
                return "Partial (30–70%)"
            return "Weak (<30%)"

        rows.append({
            "employee_id": user_id,
            "dominant_cluster": cluster_name(dom_idx),
            "dominant_weight": dom_w,
            "strength": band(dom_w),
        })
    return pd.DataFrame(rows)


@st.cache_data
def compute_systems_per_cluster() -> pd.DataFrame:
    """Count of characteristic systems per cluster (above mean in H)."""
    miner = load_miner()
    H = miner.H
    rows = [
        {
            "cluster": cluster_name(i),
            "n_systems": int((H[i] > H[i].mean()).sum()),
        }
        for i in range(N_CLUSTERS)
    ]
    return pd.DataFrame(rows).sort_values("cluster")


# ---------------------------------------------------------------------------
# Per-employee computations
# ---------------------------------------------------------------------------

@st.cache_data
def get_user_weights(user_id: int) -> pd.DataFrame:
    """Cluster weights for one employee as a sorted DataFrame."""
    miner = load_miner()
    weights = miner.get_user_role_weights(user_id)
    df = pd.DataFrame({
        "cluster": CLUSTER_LABELS,
        "weight": [float(w) for w in weights],
    }).sort_values("cluster")
    return df


@st.cache_data
def get_user_systems(user_id: int) -> list:
    """Systems the employee currently has access to."""
    matrix = load_matrix()
    row = matrix.loc[user_id]
    return row[row > 0].index.tolist()


@st.cache_data
def get_user_nonaccess_systems(user_id: int) -> list:
    """Systems the employee does NOT currently have access to."""
    matrix = load_matrix()
    user_systems = set(get_user_systems(user_id))
    return sorted(set(matrix.columns.tolist()) - user_systems)


@st.cache_data
def score_user_all_systems(user_id: int) -> pd.DataFrame:
    """Drift score for every system the employee currently accesses."""
    from role_recommender.drift.scorer import DriftScorer
    miner = load_miner()
    scorer = DriftScorer(miner)
    systems = get_user_systems(user_id)
    rows = []
    for sys_id in systems:
        r = scorer.score(user_id, sys_id)
        rows.append({
            "system_id": sys_id,
            "drift_score": r["drift_score"],
            "explanation": r["explanation"],
        })
    return (
        pd.DataFrame(rows)
        .sort_values("drift_score", ascending=False)
        .reset_index(drop=True)
    )


@st.cache_data
def score_single(user_id: int, system_id: int) -> dict:
    """Drift score for a single (employee, system) pair."""
    from role_recommender.drift.scorer import DriftScorer
    miner = load_miner()
    return DriftScorer(miner).score(user_id, system_id)


# ---------------------------------------------------------------------------
# Per-system computations
# ---------------------------------------------------------------------------

@st.cache_data
def get_system_cluster_strengths(system_id: int) -> pd.DataFrame:
    """NMF H-matrix values for each cluster for a given system."""
    miner = load_miner()
    if system_id not in miner.resource_index:
        return pd.DataFrame()
    idx = miner.resource_index.index(system_id)
    return pd.DataFrame({
        "cluster": CLUSTER_LABELS,
        "association_strength": miner.H[:, idx].tolist(),
    }).sort_values("cluster")


@st.cache_data
def get_system_employees(system_id: int) -> list:
    """Employees who currently have access to a given system."""
    matrix = load_matrix()
    if system_id not in matrix.columns:
        return []
    col = matrix[system_id]
    return col[col > 0].index.tolist()
