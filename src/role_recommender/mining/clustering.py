"""
clustering.py — k-means baseline for comparison with the NMF probabilistic model.

Used in notebooks/02_role_mining.ipynb to validate that NMF soft assignments
outperform hard k-means clustering for role interpretation.
"""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize
from loguru import logger
from role_recommender.config import RANDOM_STATE


class KMeansRoleMiner:
    """
    Hard k-means role assignment — baseline for comparison with NMF.
    Every user belongs to exactly one role cluster.
    """

    def __init__(self, n_roles: int = 15, random_state: int = RANDOM_STATE):
        self.n_roles = n_roles
        self.random_state = random_state
        self.model = KMeans(
            n_clusters=n_roles,
            random_state=random_state,
            n_init="auto",
        )
        self.labels_: np.ndarray | None = None
        self.cluster_centers_: np.ndarray | None = None
        self.user_index: list | None = None
        self.resource_index: list | None = None

    def fit(self, matrix: pd.DataFrame) -> "KMeansRoleMiner":
        self.user_index = list(matrix.index)
        self.resource_index = list(matrix.columns)
        X = normalize(matrix.values.astype(float), norm="l2")
        self.model.fit(X)
        self.labels_ = self.model.labels_
        self.cluster_centers_ = self.model.cluster_centers_
        logger.success(
            f"k-means complete: {self.n_roles} clusters, "
            f"inertia={self.model.inertia_:.2f}"
        )
        return self

    def get_user_role(self, user_id) -> int:
        idx = self.user_index.index(user_id)
        return int(self.labels_[idx])

    def get_role_permissions(self, role_id: int, top_n: int = 20) -> list:
        scores = self.cluster_centers_[role_id]
        top_idx = np.argsort(scores)[::-1][:top_n]
        return [self.resource_index[i] for i in top_idx]

    def inertia(self) -> float:
        return float(self.model.inertia_)
