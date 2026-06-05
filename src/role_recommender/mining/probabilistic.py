"""
probabilistic.py — Frank/Basin generative role-mining model (NMF approximation).
Reference: arXiv:1212.4775
"""
import numpy as np
import pandas as pd
import joblib
from sklearn.decomposition import NMF
from sklearn.preprocessing import normalize
from loguru import logger
from role_recommender.config import (
    MODELS_DIR, PROCESSED_MATRIX, ROLE_COUNT_DEFAULT, RANDOM_STATE,
)


class ProbabilisticRoleMiner:
    """
    Non-negative Matrix Factorisation approximation of the Frank/Basin
    probabilistic role-mining model.

    W (users × roles) = soft assignment of each user to roles.
    H (roles × resources) = which permissions each role grants.
    """

    def __init__(
        self,
        n_roles: int = ROLE_COUNT_DEFAULT,
        random_state: int = RANDOM_STATE,
    ):
        self.n_roles = n_roles
        self.random_state = random_state
        self.model = NMF(
            n_components=n_roles,
            init="nndsvda",
            random_state=random_state,
            max_iter=500,
        )
        self.W: np.ndarray | None = None    # users × roles
        self.H: np.ndarray | None = None    # roles × resources
        self.user_index: list | None = None
        self.resource_index: list | None = None

    def fit(self, matrix: pd.DataFrame) -> "ProbabilisticRoleMiner":
        self.user_index = list(matrix.index)
        self.resource_index = list(matrix.columns)
        X = matrix.values.astype(float)
        self.W = self.model.fit_transform(X)
        self.H = self.model.components_
        logger.success(
            f"Role mining complete: {self.n_roles} roles, "
            f"reconstruction error={self.model.reconstruction_err_:.4f}"
        )
        return self

    def get_user_role(self, user_id) -> int:
        """Return the dominant role index for a user (hard assignment)."""
        idx = self.user_index.index(user_id)
        return int(np.argmax(self.W[idx]))

    def get_user_role_weights(self, user_id) -> np.ndarray:
        """Return soft role-membership weights (L1-normalised) for a user."""
        idx = self.user_index.index(user_id)
        return normalize(self.W[idx].reshape(1, -1), norm="l1").flatten()

    def get_role_permissions(self, role_id: int, top_n: int = 20) -> list:
        """Return top-N resource IDs most associated with a role."""
        scores = self.H[role_id]
        top_idx = np.argsort(scores)[::-1][:top_n]
        return [self.resource_index[i] for i in top_idx]

    def reconstruction_error(self) -> float:
        return self.model.reconstruction_err_

    def save(self, path=None):
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        path = path or MODELS_DIR / f"role_miner_{self.n_roles}roles.joblib"
        # Store raw components — avoids __main__ pickle class-reference bug
        joblib.dump({
            "n_roles": self.n_roles,
            "random_state": self.random_state,
            "W": self.W,
            "H": self.H,
            "user_index": self.user_index,
            "resource_index": self.resource_index,
        }, path)
        logger.info(f"Model saved → {path}")
        return path

    @classmethod
    def load(cls, path) -> "ProbabilisticRoleMiner":
        data = joblib.load(path)
        # Support both old (pickled instance) and new (dict) formats
        if isinstance(data, dict):
            obj = cls(n_roles=data["n_roles"], random_state=data["random_state"])
            obj.W = data["W"]
            obj.H = data["H"]
            obj.user_index = data["user_index"]
            obj.resource_index = data["resource_index"]
            return obj
        return data  # legacy pickled instance


def train_and_save(n_roles: int = ROLE_COUNT_DEFAULT) -> ProbabilisticRoleMiner:
    matrix = pd.read_parquet(PROCESSED_MATRIX)
    miner = ProbabilisticRoleMiner(n_roles=n_roles)
    miner.fit(matrix)
    miner.save()
    return miner


if __name__ == "__main__":
    train_and_save()
