"""
analytics.py — standalone fleet analytics computation (no Streamlit dependency).

Computes balanced risk scores, anomaly rates, and risk categories for every
employee in the user-permission matrix. Can be called from the API, from
the dashboard, or from a cron/script without any Streamlit context.

Balanced Risk Score = (n_high × 1.0 + n_minor × 0.5 + n_normal × 0.0) / n_total
Risk categories are tertile-based so High / Medium / Low each contain ~⅓ of users.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def compute_fleet_analytics(miner, matrix: pd.DataFrame) -> pd.DataFrame:
    """
    Compute per-employee fleet analytics.

    Parameters
    ----------
    miner   : ProbabilisticRoleMiner — already loaded model.
    matrix  : DataFrame (index = user_id, columns = system_id, values = 0/1).

    Returns
    -------
    DataFrame with columns:
        employee_id, dominant_cluster, n_systems, n_high, n_minor, n_normal,
        balanced_risk_score, anomaly_rate, risk_category, computed_at
    """
    from role_recommender.drift.scorer import DriftScorer

    scorer = DriftScorer(miner)
    rows: list[dict] = []

    for user_id in matrix.index:
        weights = miner.get_user_role_weights(user_id)
        dom_idx = int(np.argmax(weights))
        dom_cluster = chr(65 + dom_idx)  # 0→A … 14→O

        user_row = matrix.loc[user_id]
        systems = user_row[user_row > 0].index.tolist()

        n_high = n_minor = n_normal = 0
        for sys_id in systems:
            ds = scorer.score(user_id, sys_id)["drift_score"]
            if ds >= 1.0:
                n_high += 1
            elif ds > 0.0:
                n_minor += 1
            else:
                n_normal += 1

        n_total = len(systems)
        brs = (n_high * 1.0 + n_minor * 0.5) / n_total if n_total > 0 else 0.0
        anomaly_rate = (n_high + n_minor) / n_total if n_total > 0 else 0.0

        rows.append(
            {
                "employee_id": user_id,
                "dominant_cluster": dom_cluster,
                "n_systems": n_total,
                "n_high": n_high,
                "n_minor": n_minor,
                "n_normal": n_normal,
                "balanced_risk_score": round(brs, 4),
                "anomaly_rate": round(anomaly_rate, 4),
                "computed_at": pd.Timestamp.now().isoformat(),
            }
        )

    df = pd.DataFrame(rows)

    # Tertile-based risk categories → equal thirds
    p33 = df["balanced_risk_score"].quantile(0.333)
    p67 = df["balanced_risk_score"].quantile(0.667)
    df["risk_category"] = df["balanced_risk_score"].apply(
        lambda s: "High" if s >= p67 else ("Medium" if s >= p33 else "Low")
    )

    return df
