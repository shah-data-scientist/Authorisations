"""
scorer.py — permission-overlap drift score for a new access event.

Score = 0.0  → new permission fully within role  (no drift)
Score = 0.3  → covered by a secondary role       (minor drift)
Score = 1.0  → not covered by any role           (high drift)
"""
from loguru import logger
from role_recommender.mining.probabilistic import ProbabilisticRoleMiner
from role_recommender.config import DRIFT_OVERLAP_THRESHOLD


class DriftScorer:
    def __init__(
        self,
        miner: ProbabilisticRoleMiner,
        threshold: float = DRIFT_OVERLAP_THRESHOLD,
    ):
        self.miner = miner
        self.threshold = threshold

    def score(self, user_id, new_resource_id: int) -> dict:
        """
        Score a single new access-grant event.

        Returns dict with: user_id, new_resource_id, dominant_role,
        role_permissions_sample, drift_score, is_drift, explanation.
        """
        dominant_role = self.miner.get_user_role(user_id)
        role_permissions = set(
            self.miner.get_role_permissions(dominant_role, top_n=50)
        )

        if new_resource_id in role_permissions:
            drift_score = 0.0
            explanation = (
                f"System {new_resource_id} is routinely accessed by"
                f" employees in Cluster {dominant_role}. No drift detected."
            )
        else:
            weights = self.miner.get_user_role_weights(user_id)
            any_role_covers = any(
                new_resource_id in set(
                    self.miner.get_role_permissions(r, top_n=50)
                )
                for r in range(self.miner.n_roles)
                if weights[r] > 0.05
            )
            drift_score = 0.3 if any_role_covers else 1.0
            if any_role_covers:
                explanation = (
                    f"System {new_resource_id} is occasionally accessed"
                    f" by employees in a related cluster. Minor drift."
                )
            else:
                explanation = (
                    f"System {new_resource_id} is not typically accessed"
                    f" by any cluster this user belongs to."
                    f" High drift — review recommended."
                )

        is_drift = drift_score >= self.threshold
        logger.debug(
            f"user={user_id} system={new_resource_id} "
            f"drift={drift_score:.2f} flagged={is_drift}"
        )

        return {
            "user_id": user_id,
            "system_id": new_resource_id,
            "user_cluster": dominant_role,
            "typical_systems": list(role_permissions)[:10],
            "drift_score": round(drift_score, 4),
            "is_drift": is_drift,
            "explanation": explanation,
        }
