"""
detector.py — Stage 2 XGBoost drift classifier.

Trained on historical access-removal events as implicit negative labels:
a permission that was later revoked is a weak signal it was anomalous.

Features per access event:
- drift_score (from DriftScorer)
- dominant_role
- role_weight_dominant  (soft membership weight)
- resource_frequency    (how common is this resource globally)
- user_permission_count (how many permissions does this user already have)
"""
import numpy as np
import pandas as pd
import joblib
from loguru import logger
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from role_recommender.config import (
    MODELS_DIR, PROCESSED_EVENTS, PROCESSED_MATRIX,
    DRIFT_CLASSIFIER_THRESHOLD, RANDOM_STATE,
)
from role_recommender.mining.probabilistic import ProbabilisticRoleMiner
from role_recommender.drift.scorer import DriftScorer


def build_features(
    events: pd.DataFrame,
    miner: ProbabilisticRoleMiner,
    matrix: pd.DataFrame,
) -> pd.DataFrame:
    """Build feature matrix from raw events + mined roles."""
    scorer = DriftScorer(miner)
    resource_freq = matrix.sum(axis=0) / len(matrix)  # fraction of users with access
    user_perm_count = matrix.sum(axis=1)               # number of resources per user

    rows = []
    for _, row in events.iterrows():
        user_id = row.get("ROLE_CODE")
        resource_id = row.get("RESOURCE")

        if user_id not in miner.user_index:
            continue
        if resource_id not in miner.resource_index:
            continue

        score_result = scorer.score(user_id, resource_id)
        weights = miner.get_user_role_weights(user_id)
        dominant = score_result["dominant_role"]

        rows.append({
            "drift_score": score_result["drift_score"],
            "dominant_role": dominant,
            "role_weight_dominant": float(weights[dominant]),
            "resource_frequency": float(resource_freq.get(resource_id, 0.0)),
            "user_permission_count": int(user_perm_count.get(user_id, 0)),
            "ACTION": int(row.get("ACTION", 1)),  # 1=granted, 0=revoked
        })

    return pd.DataFrame(rows)


class DriftClassifier:
    def __init__(self, threshold: float = DRIFT_CLASSIFIER_THRESHOLD):
        self.threshold = threshold
        self.model = XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            scale_pos_weight=10,  # handles class imbalance (removals << grants)
            random_state=RANDOM_STATE,
            eval_metric="logloss",
        )
        self._fitted = False

    def fit(self, features: pd.DataFrame) -> "DriftClassifier":
        # Label: ACTION==0 (revoked) = anomalous = 1 in drift sense
        X = features.drop(columns=["ACTION"])
        y = (features["ACTION"] == 0).astype(int)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
        )
        self.model.fit(X_train, y_train)
        preds = self.model.predict(X_test)
        logger.info("\n" + classification_report(y_test, preds))
        self._fitted = True
        return self

    def predict_proba(self, feature_row: dict) -> float:
        """Return drift probability for a single event feature dict."""
        X = pd.DataFrame([feature_row]).reindex(
            columns=["drift_score", "dominant_role", "role_weight_dominant",
                     "resource_frequency", "user_permission_count"],
            fill_value=0,
        )
        return float(self.model.predict_proba(X)[0, 1])

    def save(self, path=None):
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        path = path or MODELS_DIR / "drift_classifier.joblib"
        joblib.dump(self, path)
        logger.info(f"Classifier saved → {path}")

    @classmethod
    def load(cls, path) -> "DriftClassifier":
        return joblib.load(path)


def train_and_save() -> DriftClassifier:
    events = pd.read_parquet(PROCESSED_EVENTS)
    matrix = pd.read_parquet(PROCESSED_MATRIX)

    model_path = next(
        (p for p in MODELS_DIR.glob("role_miner_*.joblib")),
        None,
    )
    if model_path is None:
        raise FileNotFoundError("Train the role miner first: make train")

    miner = ProbabilisticRoleMiner.load(model_path)
    features = build_features(events, miner, matrix)

    if features.empty:
        logger.warning("No features built — skipping classifier training.")
        return DriftClassifier()

    clf = DriftClassifier()
    clf.fit(features)
    clf.save()
    return clf


if __name__ == "__main__":
    train_and_save()
