"""
scorer.py — continuous NMF cosine drift score for a new access event.

Drift score = 1 − cosine_similarity(W[user], H[:, system])

Where W[user] is the employee's soft role membership vector (shape: n_roles)
and H[:, system] is the system's NMF loading across all roles (shape: n_roles).

A high dot product means the employee's role profile strongly overlaps with
the system's role profile → low drift. A low dot product means the system
belongs to roles the employee is not part of → high drift.

Score thresholds (from config):
    < 0.3  → Normal      (system fits the employee's role profile well)
    0.3–0.7 → Minor Drift (partial role overlap)
    ≥ 0.7  → High Drift  (system is outside the employee's role profile)
"""
import numpy as np
from loguru import logger

from role_recommender.config import (
    DRIFT_NORMAL_THRESHOLD,
    DRIFT_HIGH_THRESHOLD,
    DRIFT_CLASSIFIER_THRESHOLD,
)
from role_recommender.mining.probabilistic import ProbabilisticRoleMiner


class DriftScorer:
    def __init__(
        self,
        miner: ProbabilisticRoleMiner,
        threshold: float = DRIFT_CLASSIFIER_THRESHOLD,
    ):
        self.miner = miner
        self.threshold = threshold

    def _cosine_drift(self, user_id, resource_id: int) -> float:
        """Continuous drift score via NMF cosine similarity."""
        user_idx = self.miner.user_index.index(user_id)
        user_vec = self.miner.W[user_idx]                         # (n_roles,)

        sys_idx = self.miner.resource_index.index(resource_id)
        sys_vec = self.miner.H[:, sys_idx]                        # (n_roles,)

        norm = np.linalg.norm(user_vec) * np.linalg.norm(sys_vec)
        similarity = float(np.dot(user_vec, sys_vec)) / (norm + 1e-9)
        return round(float(1.0 - similarity), 4)

    def score(self, user_id, new_resource_id: int) -> dict:
        """
        Score a single new access-grant event.

        Returns dict with: user_id, system_id, user_cluster, drift_score,
        drift_category, is_drift, explanation, typical_systems.
        """
        dominant_role = self.miner.get_user_role(user_id)
        role_permissions = list(
            self.miner.get_role_permissions(dominant_role, top_n=10)
        )

        drift_score = self._cosine_drift(user_id, new_resource_id)

        if drift_score < DRIFT_NORMAL_THRESHOLD:
            drift_category = "Normal"
            explanation = (
                f"System {new_resource_id} fits the employee's role profile"
                f" (Cluster {dominant_role}). No drift detected."
            )
        elif drift_score < DRIFT_HIGH_THRESHOLD:
            drift_category = "Minor Drift"
            explanation = (
                f"System {new_resource_id} has partial overlap with the"
                f" employee's role profile (Cluster {dominant_role})."
                f" Minor drift — quick review recommended."
            )
        else:
            drift_category = "High Drift"
            explanation = (
                f"System {new_resource_id} is outside the employee's role"
                f" profile (Cluster {dominant_role}). High drift —"
                f" escalate for review."
            )

        is_drift = drift_score >= self.threshold

        logger.debug(
            f"user={user_id} system={new_resource_id} "
            f"drift={drift_score:.4f} category={drift_category}"
        )

        return {
            "user_id": user_id,
            "system_id": new_resource_id,
            "user_cluster": dominant_role,
            "typical_systems": role_permissions,
            "drift_score": drift_score,
            "drift_category": drift_category,
            "is_drift": is_drift,
            "explanation": explanation,
        }
