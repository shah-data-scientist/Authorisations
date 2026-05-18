"""
explainer.py — SHAP-based explanation of drift flag decisions.

Per the 2026 ITDR Market Outlook, enterprise buyers require
"evidence-grade reporting" — a flagged event with no explanation
is not actionable. SHAP provides per-feature attribution.
"""
import numpy as np
import pandas as pd
from loguru import logger

try:
    import shap
    _SHAP_AVAILABLE = True
except ImportError:
    _SHAP_AVAILABLE = False
    logger.warning("shap not installed — explanations will be unavailable.")

from role_recommender.drift.detector import DriftClassifier

FEATURE_COLS = [
    "drift_score",
    "dominant_role",
    "role_weight_dominant",
    "resource_frequency",
    "user_permission_count",
]


class DriftExplainer:
    def __init__(self, classifier: DriftClassifier):
        self.classifier = classifier
        self._explainer = None

    def _get_explainer(self):
        if not _SHAP_AVAILABLE:
            return None
        if self._explainer is None:
            self._explainer = shap.TreeExplainer(self.classifier.model)
        return self._explainer

    def explain(self, feature_row: dict) -> dict:
        """
        Return SHAP values for a single event.

        Returns dict: {feature_name: shap_value} sorted by abs contribution,
        plus 'base_value' (expected model output).
        """
        explainer = self._get_explainer()
        if explainer is None:
            return {"error": "shap not available"}

        X = pd.DataFrame([feature_row]).reindex(columns=FEATURE_COLS, fill_value=0)
        shap_values = explainer.shap_values(X)

        # For binary classifiers, shap_values may be a list [neg_class, pos_class]
        if isinstance(shap_values, list):
            vals = shap_values[1][0]
        else:
            vals = shap_values[0]

        contributions = dict(zip(FEATURE_COLS, vals.tolist()))
        contributions_sorted = dict(
            sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)
        )
        return {
            "base_value": float(explainer.expected_value[1]
                                if isinstance(explainer.expected_value, (list, np.ndarray))
                                else explainer.expected_value),
            "feature_contributions": contributions_sorted,
            "top_reason": max(contributions, key=lambda k: abs(contributions[k])),
        }
